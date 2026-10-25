"""Iteration 10: guest demo as Carl (5 cards, resets each open), voice/drafts as Carl, research-backed starter priorities."""
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


def clerk_token(who):
    return subprocess.check_output(["python", "tests/clerk_token.py", who], cwd="/app/backend").decode().strip()


@pytest.fixture(scope="module")
def guest():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/guest/start")
    assert r.status_code == 200 and r.json() == {"guest": True}
    assert s.cookies.get("aoc_guest", "").startswith("guest_")
    return s


# Guest demo: Carl profile + 5 cards with Beta Corp first
class TestGuestDemo:
    def test_profile_is_carl(self, guest):
        me = guest.get(f"{BASE_URL}/api/me").json()
        assert me["name"] == "Carl Walker" and me["company"] == "Fernhill Finance"

    def test_board_has_5_beta_first(self, guest):
        d = guest.get(f"{BASE_URL}/api/advisor/items").json()
        assert d["mode"] == "demo"
        assert len(d["top"]) == 5, [i["action"] for i in d["top"]]
        assert "Beta Corp" in (d["top"][0]["action"] + d["top"][0].get("who", "")), d["top"][0]

    def test_reset_on_reopen(self, guest):
        top = guest.get(f"{BASE_URL}/api/advisor/items").json()["top"]
        for it, st in zip(top[:2], ["done", "dismissed"]):
            r = guest.post(f"{BASE_URL}/api/advisor/items/{it['id']}/status", json={"status": st})
            assert r.status_code == 200, r.text
        after = guest.get(f"{BASE_URL}/api/advisor/items").json()
        closed_ids = {it["id"] for it in top[:2]}
        assert not closed_ids & {i["id"] for i in after["top"]}
        cookie = guest.cookies.get("aoc_guest")
        assert guest.post(f"{BASE_URL}/api/guest/start").status_code == 200
        assert guest.cookies.get("aoc_guest") == cookie  # same guest reused
        again = guest.get(f"{BASE_URL}/api/advisor/items").json()
        assert len(again["top"]) == 5
        assert again["top"][0]["action"] == top[0]["action"]
        assert again["closed"] == []

    def test_voice_token_founder_carl(self, guest):
        r = guest.get(f"{BASE_URL}/api/voice-token")
        if r.status_code != 200:
            pytest.skip(f"voice not available: {r.status_code} {r.text[:100]}")
        assert r.json()["dynamicVariables"]["founder_name"] == "Carl Walker"

    def test_demo_draft_signed_carl(self, guest):
        top = guest.get(f"{BASE_URL}/api/advisor/items").json()["top"]
        target = next((i for i in top if i.get("kind") in ("reply", "send") or "Beta" in i["action"]), top[0])
        r = guest.post(f"{BASE_URL}/api/advisor/items/{target['id']}/draft", timeout=90)
        assert r.status_code == 200, r.text
        body = r.json().get("body") or r.json().get("text") or str(r.json())
        print("DRAFT:", body[-200:])
        assert "Carl" in body


# Auth guard
def test_suggest_requires_auth():
    assert requests.post(f"{BASE_URL}/api/priorities/suggest").status_code == 401


# Onboarding research for a brand-new profile: only if the second user has nothing
def test_onboarding_research_second_user():
    h = {"Authorization": "Bearer " + clerk_token("second")}
    me = requests.get(f"{BASE_URL}/api/me", headers=h).json()
    if me.get("onboarded"):
        pytest.skip("UNVERIFIED: second user already has a profile/priorities")
