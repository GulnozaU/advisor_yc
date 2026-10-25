# Iteration 5: live-mode upstream failures must return 424 JSON (not Cloudflare 502 HTML) for a signed-in founder
import os
import subprocess

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def founder():
    tok = subprocess.check_output(["python", "tests/clerk_token.py", "founder"], cwd="/app/backend").decode().strip()
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "Origin": BASE_URL})
    r = s.post(f"{BASE_URL}/api/advisor/mode", json={"mode": "live"}, timeout=60)
    print("set live:", r.status_code, r.text[:200])
    yield s
    r = s.post(f"{BASE_URL}/api/advisor/mode", json={"mode": "manual"}, timeout=60)
    assert r.status_code == 200 and r.json()["mode"] == "manual"


def _check(r, phrase):
    print(r.request.method, r.url, r.status_code, r.headers.get("content-type"), r.text[:200])
    assert r.status_code == 424
    assert "application/json" in r.headers.get("content-type", "")
    detail = r.json()["detail"]
    assert phrase in detail
    return detail


def test_google_connect_424(founder):
    _check(founder.post(f"{BASE_URL}/api/advisor/google/connect", json={"toolkit": "gmail"}, timeout=60), "Starting the Google connection failed")


def test_google_status_424(founder):
    _check(founder.get(f"{BASE_URL}/api/advisor/google/status", timeout=60), "Checking Google connection failed")


def test_sync_live_424(founder):
    _check(founder.post(f"{BASE_URL}/api/advisor/sync", timeout=90), "Sync failed")


def test_competitors_find_424(founder):
    _check(founder.post(f"{BASE_URL}/api/advisor/competitors/find", timeout=60), "Finding competitors failed")


def test_no_auth_401():
    r = requests.post(f"{BASE_URL}/api/advisor/google/connect", json={"toolkit": "gmail"}, timeout=30)
    assert r.status_code == 401
