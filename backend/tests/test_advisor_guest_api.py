# Founder Advisor + guest demo API regression tests (guest cookie, ranking, draft/send, lookup, demo events, isolation)
import os
import sys
import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, os.path.dirname(__file__))
from clerk_helpers import session_token, FOUNDER  # noqa: E402

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
_E = dotenv_values("/app/backend/.env")


def _mongo():
    from pymongo import MongoClient
    return MongoClient(_E["MONGO_URL"])[_E["DB_NAME"]]


def new_guest():
    s = requests.Session()
    r = s.post(f"{BASE}/guest/start", json={}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json() == {"guest": True}
    assert s.cookies.get("aoc_guest", "").startswith("guest_")
    return s


@pytest.fixture(scope="module")
def guests():
    a, b = new_guest(), new_guest()
    yield a, b
    db = _mongo()
    ids = [a.cookies.get("aoc_guest"), b.cookies.get("aoc_guest")]
    for col in ("items", "overrides", "market_events", "demo_extra", "drafts", "sends", "rank_state", "memories", "competitors", "calls"):
        db[col].delete_many({"uid": {"$in": ids}})
    db.calls.delete_many({"user_id": {"$in": ids}})
    db.profiles.delete_many({"user_id": {"$in": ids}})
    db.guests.delete_many({"uid": {"$in": ids}})


# --- auth ---
class TestGuestAuth:
    def test_no_auth_401(self):
        assert requests.get(f"{BASE}/advisor/items", timeout=20).status_code == 401
        assert requests.get(f"{BASE}/me", timeout=20).status_code == 401

    def test_forged_cookie_401(self):
        r = requests.get(f"{BASE}/advisor/items", cookies={"aoc_guest": "guest_" + "a" * 32}, timeout=20)
        assert r.status_code == 401
        r = requests.get(f"{BASE}/advisor/items", cookies={"aoc_guest": "not-a-guest"}, timeout=20)
        assert r.status_code == 401

    def test_guest_me(self, guests):
        r = guests[0].get(f"{BASE}/me", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["name"] == "Mira Chen" and d["company"] == "Northwind" and d["onboarded"] is True

    def test_guest_start_idempotent(self, guests):
        gid = guests[0].cookies.get("aoc_guest")
        r = guests[0].post(f"{BASE}/guest/start", json={}, timeout=20)
        assert r.status_code == 200
        assert guests[0].cookies.get("aoc_guest") == gid


# --- ranking ---
class TestRanking:
    def test_top5_order(self, guests):
        r = guests[0].get(f"{BASE}/advisor/items", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["mode"] == "demo"
        top = d["top"]
        assert len(top) == 5
        acts = [t["action"].lower() + " " + (t.get("target") or "").lower() for t in top]
        print(acts)
        assert "beta" in acts[0]
        assert "priya" in acts[1]
        assert "acme" in acts[2] or "dana" in acts[2]
        assert "tom" in acts[3]
        assert top[4]["source"] == "playbook"
        assert all("uid" not in t for t in top)
        assert set(top[0]["score_parts"]).issuperset({"S", "L", "U", "E"})

    def test_guest_cannot_switch_mode(self, guests):
        for m in ("manual", "live"):
            r = guests[0].post(f"{BASE}/advisor/mode", json={"mode": m}, timeout=20)
            assert r.status_code == 403
            assert "Sign up" in r.json()["detail"]

    def test_guest_cannot_google(self, guests):
        assert guests[0].post(f"{BASE}/advisor/google/connect", json={"toolkit": "gmail"}, timeout=20).status_code == 403
        assert guests[0].get(f"{BASE}/advisor/google/status", timeout=20).status_code == 403
        assert guests[0].post(f"{BASE}/advisor/competitors/find", timeout=20).status_code == 403


# --- draft / send ---
class TestDraftSend:
    def test_draft_and_send_once(self, guests):
        s = guests[1]
        top = s.get(f"{BASE}/advisor/items", timeout=20).json()["top"]
        beta = top[0]
        r = s.post(f"{BASE}/advisor/items/{beta['id']}/draft", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["to"] == "ceo@betacorp.example.com"
        assert any(c.startswith("ops@") for c in d["cc"])
        assert "Template draft" in d["body"]
        assert "uid" not in d
        # same draft on second request
        assert s.post(f"{BASE}/advisor/items/{beta['id']}/draft", timeout=30).json()["id"] == d["id"]
        r1 = s.post(f"{BASE}/advisor/drafts/{d['id']}/send", timeout=30)
        assert r1.status_code == 200 and r1.json()["result"] == "simulated"
        assert beta["id"] not in [t["id"] for t in r1.json()["top"]]
        r2 = s.post(f"{BASE}/advisor/drafts/{d['id']}/send", timeout=30)
        assert r2.json()["result"] == "already_sent"
        closed = s.get(f"{BASE}/advisor/items", timeout=20).json()["closed"]
        assert any(c["id"] == beta["id"] and c["status"] == "done" for c in closed)

    def test_draft_playbook_400(self, guests):
        top = guests[1].get(f"{BASE}/advisor/items", timeout=20).json()["top"]
        pb = next((t for t in top if t["source"] == "playbook"), None)
        if not pb:
            pytest.skip("no playbook item")
        assert guests[1].post(f"{BASE}/advisor/items/{pb['id']}/draft", timeout=20).status_code == 400

    def test_send_unknown_404(self, guests):
        assert guests[1].post(f"{BASE}/advisor/drafts/nope/send", timeout=20).status_code == 404

    def test_done_dismiss(self, guests):
        s = guests[1]
        top = s.get(f"{BASE}/advisor/items", timeout=20).json()["top"]
        a, b = top[0]["id"], top[1]["id"]
        r = s.post(f"{BASE}/advisor/items/{a}/status", json={"status": "done"}, timeout=20)
        assert r.status_code == 200 and a not in [t["id"] for t in r.json()["top"]]
        r = s.post(f"{BASE}/advisor/items/{b}/status", json={"status": "dismissed"}, timeout=20)
        assert r.status_code == 200 and b not in [t["id"] for t in r.json()["top"]]
        assert s.post(f"{BASE}/advisor/items/bogus/status", json={"status": "done"}, timeout=20).status_code == 404
        assert s.post(f"{BASE}/advisor/items/{a}/status", json={"status": "weird"}, timeout=20).status_code == 422


# --- lookup + isolation ---
class TestLookup:
    def test_lookup_beta(self, guests):
        r = guests[0].post(f"{BASE}/advisor/lookup", json={"query": "Beta Corp tier 2"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        print(d["result"][:500])
        assert d["count"] > 0 and "<untrusted>" in d["result"] and "Beta" in d["result"]

    def test_lookup_nonsense(self, guests):
        r = guests[0].post(f"{BASE}/advisor/lookup", json={"query": "zzqxv flurbnog"}, timeout=20)
        assert r.json()["count"] == 0 and "No matching records" in r.json()["result"]

    def test_lookup_validation(self, guests):
        assert guests[0].post(f"{BASE}/advisor/lookup", json={"query": ""}, timeout=20).status_code == 422

    def test_isolation_items(self, guests):
        # item ids are deterministic per demo story; isolation is by uid. Guest B closed beta earlier -> A must still have it open
        a_top = guests[0].get(f"{BASE}/advisor/items", timeout=20).json()["top"]
        b = guests[1].get(f"{BASE}/advisor/items", timeout=20).json()
        assert a_top[0]["id"] == "thread-t-beta"
        assert "thread-t-beta" not in [t["id"] for t in b["top"]]
        assert any(c["id"] == "thread-t-beta" for c in b["closed"])
        a_closed = guests[0].get(f"{BASE}/advisor/items", timeout=20).json()["closed"]
        assert a_closed == []
        # B's draft not visible to A
        did = _mongo().drafts.find_one({"uid": guests[1].cookies.get("aoc_guest")})["id"]
        assert guests[0].get(f"{BASE}/advisor/drafts/{did}", timeout=20).status_code == 404
        assert guests[0].post(f"{BASE}/advisor/drafts/{did}/send", timeout=20).status_code == 404

    def test_isolation_lookup_from_signed_in(self, guests):
        # founder lookup must not see guest-only data (guest B's done status / other guest uids)
        tok = session_token(FOUNDER)
        r = requests.post(f"{BASE}/advisor/lookup", json={"query": "Beta Corp tier 2"}, headers={"Authorization": f"Bearer {tok}"}, timeout=20)
        assert r.status_code == 200
        assert "guest_" not in r.json()["result"]


# --- demo events ---
class TestDemoEvents:
    def test_price_cut_then_investor(self):
        s = new_guest()
        try:
            r = s.post(f"{BASE}/advisor/demo/event", json={"kind": "price_cut"}, timeout=30)
            assert r.status_code == 200
            top = r.json()["top"]
            print([t["action"] for t in top])
            assert top[2]["source"] == "market" and "rivalyst" in (top[2]["action"] + top[2]["why"]).lower()
            r = s.post(f"{BASE}/advisor/demo/event", json={"kind": "investor_email"}, timeout=30)
            top = r.json()["top"]
            print([t["action"] for t in top])
            assert any("alex" in (t["action"] + (t.get("target") or "")).lower() for t in top[:3])
            assert r.json()["event"].startswith("[EVENT]")
            # reprioritize
            rp = s.post(f"{BASE}/advisor/items/{top[0]['id']}/reprioritize", json={"reason": "not important, later"}, timeout=30)
            assert rp.status_code == 200 and rp.json()["top"][0]["id"] != top[0]["id"]
        finally:
            gid = s.cookies.get("aoc_guest")
            db = _mongo()
            for col in ("items", "overrides", "market_events", "demo_extra", "drafts", "sends", "rank_state", "memories"):
                db[col].delete_many({"uid": gid})
            db.profiles.delete_many({"user_id": gid})
            db.guests.delete_many({"uid": gid})

    def test_voice_token_guest(self, guests):
        r = guests[0].get(f"{BASE}/voice-token", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["advisor"] is True and d["signedUrl"].startswith("wss://")
        assert "Beta" in d["dynamicVariables"]["opening_line"] or "Sam" in d["dynamicVariables"]["opening_line"]
        print(d["dynamicVariables"]["opening_line"])


# --- signed-in founder regression: mode switching ---
class TestFounderMode:
    def test_manual_and_demo(self):
        h = {"Authorization": f"Bearer {session_token(FOUNDER)}"}
        r = requests.post(f"{BASE}/advisor/mode", json={"mode": "manual"}, headers=h, timeout=30)
        assert r.status_code == 200 and r.json()["items"] == []
        d = requests.get(f"{BASE}/advisor/items", headers=h, timeout=20).json()
        assert d["mode"] == "manual" and d["top"] == []
        r = requests.post(f"{BASE}/advisor/mode", json={"mode": "demo"}, headers=h, timeout=30)
        assert r.status_code == 200 and len(r.json()["items"]) == 5
        assert "beta" in r.json()["items"][0]["action"].lower()
