# Draft Fill-ins: backend guard on [placeholder] at POST /advisor/drafts/{id}/send (guest demo)
import re
import pytest
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
_E = dotenv_values("/app/backend/.env")
PH = re.compile(r"\[[^\[\]\n]{1,60}\]")


def _mongo():
    from pymongo import MongoClient
    return MongoClient(_E["MONGO_URL"])[_E["DB_NAME"]]


@pytest.fixture(scope="module")
def guest():
    s = requests.Session()
    assert s.post(f"{BASE}/guest/start", json={}, timeout=30).status_code == 200
    yield s
    gid = s.cookies.get("aoc_guest")
    db = _mongo()
    for col in ("items", "overrides", "market_events", "demo_extra", "drafts", "sends", "rank_state", "memories", "guests"):
        db[col].delete_many({"uid": gid})


def _beta(s):
    top = s.get(f"{BASE}/advisor/items", timeout=20).json()["top"]
    return next(t for t in top if "beta" in (t.get("id", "") + str(t.get("title", ""))).lower() or t.get("thread_id") == "t-beta")


class TestFillins:
    state = {}

    def test_draft_has_placeholder(self, guest):
        beta = _beta(guest)
        r = guest.post(f"{BASE}/advisor/items/{beta['id']}/draft", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        print("DRAFT:", d["body"])
        self.state.update(d=d, beta=beta)
        assert PH.search(d["body"]), "Claude draft had no placeholder"

    def test_send_without_body_blocked(self, guest):
        d = self.state["d"]
        if not PH.search(d["body"]):
            pytest.skip("no placeholder")
        r = guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", timeout=30)
        assert r.status_code == 400
        assert r.json()["detail"] == "Fill in every [placeholder] before sending."

    def test_send_with_placeholder_body_blocked(self, guest):
        d = self.state["d"]
        r = guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": "Hi Sam, Tier 2 is [price]. Thanks"}, timeout=30)
        assert r.status_code == 400
        assert r.json()["detail"] == "Fill in every [placeholder] before sending."
        items = guest.get(f"{BASE}/advisor/items", timeout=20).json()
        assert self.state["beta"]["id"] in [t["id"] for t in items["top"]]
        assert guest.get(f"{BASE}/advisor/drafts/{d['id']}", timeout=20).status_code == 200
        assert _mongo().sends.count_documents({"draft_id": d["id"]}) == 0

    def test_send_filled_body(self, guest):
        d = self.state["d"]
        body = "Hi Sam, Tier 2 is $499/month. TEST_filled"
        r = guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": body}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["result"] == "simulated"
        assert self.state["beta"]["id"] not in [t["id"] for t in r.json()["top"]]
        g = guest.get(f"{BASE}/advisor/drafts/{d['id']}", timeout=20).json()
        assert g["body"] == body
        assert "uid" not in g and "_id" not in g

    def test_resend_already_sent(self, guest):
        d = self.state["d"]
        r = guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": "Hi Sam, Tier 2 is $499/month. TEST_filled"}, timeout=30)
        assert r.status_code == 200 and r.json()["result"] == "already_sent"

    def test_resend_after_sent_with_placeholder(self, guest):
        # A sent draft should not be re-edited with a placeholder
        d = self.state["d"]
        r = guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": "edited [x]"}, timeout=30)
        g = guest.get(f"{BASE}/advisor/drafts/{d['id']}", timeout=20).json()
        print("resend status", r.status_code, r.text[:200], "body now:", g["body"])
        assert g["body"] == "Hi Sam, Tier 2 is $499/month. TEST_filled", "sent draft body was overwritten after send"

    def test_unknown_draft_404(self, guest):
        assert guest.post(f"{BASE}/advisor/drafts/nope/send", json={"body": "x"}, timeout=20).status_code == 404

    def test_body_too_long_422(self, guest):
        d = self.state["d"]
        assert guest.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": "a" * 5001}, timeout=20).status_code == 422


class TestNoPlaceholderDraft:
    def test_no_placeholder_sends_immediately(self):
        s = requests.Session()
        s.post(f"{BASE}/guest/start", json={}, timeout=30)
        gid = s.cookies.get("aoc_guest")
        try:
            top = s.get(f"{BASE}/advisor/items", timeout=20).json()["top"]
            for it in top:
                r = s.post(f"{BASE}/advisor/items/{it['id']}/draft", timeout=60)
                if r.status_code != 200:
                    continue
                d = r.json()
                print(it["id"], "placeholders:", PH.findall(d["body"]))
                if not PH.search(d["body"]):
                    r2 = s.post(f"{BASE}/advisor/drafts/{d['id']}/send", timeout=30)
                    assert r2.status_code == 200 and r2.json()["result"] == "simulated"
                    return
            # fall back: replace body with clean text on the last draft (same as user editing)
            r2 = s.post(f"{BASE}/advisor/drafts/{d['id']}/send", json={"body": "Clean text"}, timeout=30)
            assert r2.status_code == 200
        finally:
            db = _mongo()
            for col in ("items", "overrides", "market_events", "demo_extra", "drafts", "sends", "rank_state", "memories", "guests"):
                db[col].delete_many({"uid": gid})
