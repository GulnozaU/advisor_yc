# Advisor on Call founder dashboard (React+FastAPI) - API regression tests
import sys
import os
import pytest
import requests
from datetime import datetime, timezone
from dotenv import dotenv_values

sys.path.insert(0, os.path.dirname(__file__))
from clerk_helpers import session_token, create_temp_user, delete_user, FOUNDER  # noqa: E402

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"


def client(tok):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def temp_users():
    a, b = create_temp_user(), create_temp_user()
    yield a, b
    delete_user(a)
    delete_user(b)
    from pymongo import MongoClient
    e = dotenv_values("/app/backend/.env")
    db = MongoClient(e["MONGO_URL"])[e["DB_NAME"]]
    for coll in ("profiles", "priorities", "calls"):
        db[coll].delete_many({"user_id": {"$in": [a, b]}})


@pytest.fixture(scope="module")
def ca(temp_users):
    return client(session_token(temp_users[0]))


@pytest.fixture(scope="module")
def cb(temp_users):
    return client(session_token(temp_users[1]))


PROFILE = {"name": "TEST Ana Ruiz", "company": "TEST Co", "one_liner": "x", "website": "t.co", "goal": "raise"}


# Public endpoints
def test_public():
    assert requests.get(f"{BASE}/health").status_code == 200
    r = requests.get(f"{BASE}/clerk/config")
    assert r.status_code == 200 and r.json()["enabled"] is True


# Auth: 401 without token
@pytest.mark.parametrize("m,p", [("get", "/me"), ("put", "/me"), ("get", "/priorities"), ("post", "/priorities"),
                                  ("post", "/priorities/reorder"), ("patch", "/priorities/x"), ("delete", "/priorities/x"),
                                  ("get", "/calls"), ("post", "/calls"), ("get", "/voice-token")])
def test_401(m, p):
    r = requests.request(m, f"{BASE}{p}", json={})
    assert r.status_code == 401, (p, r.status_code, r.text)
    r2 = requests.request(m, f"{BASE}{p}", json={}, headers={"Authorization": "Bearer garbage"})
    assert r2.status_code == 401, (p, r2.status_code)


# Profile + seeding
def test_me_and_seed(ca):
    r = ca.get(f"{BASE}/me")
    assert r.status_code == 200 and r.json()["onboarded"] is False
    r = ca.put(f"{BASE}/me", json=PROFILE)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == PROFILE["name"] and r.json()["onboarded"] is True
    pr = ca.get(f"{BASE}/priorities").json()
    assert len(pr) == 3 and all(p["sample"] for p in pr)
    r = ca.put(f"{BASE}/me", json={**PROFILE, "name": "TEST Ana B", "goal": "ship"})
    assert r.status_code == 200
    assert len(ca.get(f"{BASE}/priorities").json()) == 3
    me = ca.get(f"{BASE}/me").json()
    assert me["name"] == "TEST Ana B" and me["goal"] == "ship" and me["onboarded"] is True


def test_profile_validation(ca):
    assert ca.put(f"{BASE}/me", json={**PROFILE, "goal": "nope"}).status_code == 422
    assert ca.put(f"{BASE}/me", json={**PROFILE, "name": ""}).status_code == 422


# Priorities CRUD + status + reorder
def test_priorities_flow(ca):
    r = ca.post(f"{BASE}/priorities", json={"type": "learn", "action": "TEST learn x", "who": "me", "reason": "r",
                                            "deadline": datetime.now(timezone.utc).isoformat()})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["rank"] == 3 and p["status"] == "open" and p["sample"] is False
    r = ca.patch(f"{BASE}/priorities/{p['id']}", json={"action": "TEST edited", "type": "decide"})
    assert r.status_code == 200 and r.json()["action"] == "TEST edited" and r.json()["type"] == "decide"
    ids = [x["id"] for x in ca.get(f"{BASE}/priorities").json()]
    new_order = list(reversed(ids))
    assert ca.post(f"{BASE}/priorities/reorder", json={"ids": new_order}).status_code == 200
    assert [x["id"] for x in ca.get(f"{BASE}/priorities").json()] == new_order
    # done -> closed
    assert ca.patch(f"{BASE}/priorities/{p['id']}", json={"status": "done"}).json()["closed_at"]
    assert p["id"] not in [x["id"] for x in ca.get(f"{BASE}/priorities").json()]
    closed = ca.get(f"{BASE}/priorities?status=closed").json()
    assert p["id"] in [x["id"] for x in closed]
    # reopen
    r = ca.patch(f"{BASE}/priorities/{p['id']}", json={"status": "open"})
    assert r.json()["closed_at"] is None
    assert ca.get(f"{BASE}/priorities").json()[-1]["id"] == p["id"]
    # dismissed
    ca.patch(f"{BASE}/priorities/{p['id']}", json={"status": "dismissed"})
    assert any(x["id"] == p["id"] and x["status"] == "dismissed" for x in ca.get(f"{BASE}/priorities?status=closed").json())
    # delete
    assert ca.delete(f"{BASE}/priorities/{p['id']}").status_code == 200
    assert ca.delete(f"{BASE}/priorities/{p['id']}").status_code == 404
    assert p["id"] not in [x["id"] for x in ca.get(f"{BASE}/priorities?status=closed").json()]


def test_priority_validation(ca):
    assert ca.post(f"{BASE}/priorities", json={"type": "bad", "action": "x"}).status_code == 422
    assert ca.post(f"{BASE}/priorities", json={"type": "send", "action": ""}).status_code == 422
    assert ca.get(f"{BASE}/priorities?status=weird").status_code == 422


# Isolation
def test_isolation(ca, cb):
    pid = ca.get(f"{BASE}/priorities").json()[0]["id"]
    assert cb.get(f"{BASE}/priorities").json() == []
    assert cb.get(f"{BASE}/priorities?status=closed").json() == []
    assert cb.get(f"{BASE}/calls").json() == []
    assert cb.patch(f"{BASE}/priorities/{pid}", json={"action": "hack"}).status_code == 404
    assert cb.delete(f"{BASE}/priorities/{pid}").status_code == 404
    cb.post(f"{BASE}/priorities/reorder", json={"ids": [pid]})
    assert ca.get(f"{BASE}/priorities").json()[0]["id"] == pid
    # B saving a call with A's priority ids should not leak A's priorities
    r = cb.post(f"{BASE}/calls", json={"started_at": datetime.now(timezone.utc).isoformat(), "duration_sec": 1, "priority_ids": [pid]})
    assert r.status_code == 200 and r.json()["priorities"] == []


# Voice token + calls
def test_voice_token(ca):
    r = ca.get(f"{BASE}/voice-token", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["signedUrl"].startswith("wss://")
    dv = d["dynamicVariables"]
    for k in ["founder_name", "company", "goal", "top_priority", "priorities"]:
        assert k in dv and isinstance(dv[k], str)
    assert dv["founder_name"] == "TEST Ana B" and dv["goal"] == "Ship"
    open_ids = [x["id"] for x in ca.get(f"{BASE}/priorities").json()]
    assert d["priorityIds"] == open_ids[:5]
    assert dv["top_priority"] == ca.get(f"{BASE}/priorities").json()[0]["action"]


def test_calls(ca):
    ids = [x["id"] for x in ca.get(f"{BASE}/priorities").json()]
    r1 = ca.post(f"{BASE}/calls", json={"started_at": "2026-01-01T10:00:00+00:00", "duration_sec": 30, "priority_ids": ids})
    r2 = ca.post(f"{BASE}/calls", json={"started_at": "2026-01-02T10:00:00+00:00", "duration_sec": 60, "priority_ids": ids[:1]})
    assert r1.status_code == 200 and len(r1.json()["priorities"]) == 3
    calls = ca.get(f"{BASE}/calls").json()
    assert [c["id"] for c in calls[:2]] == [r2.json()["id"], r1.json()["id"]]
    assert ca.post(f"{BASE}/calls", json={"started_at": "x", "duration_sec": -1}).status_code == 422


def test_founder_token_works():
    c = client(session_token(FOUNDER))
    me = c.get(f"{BASE}/me").json()
    assert me["onboarded"] is True and me["name"] == "Maya Chen"
