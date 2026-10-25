# Advisor on Call - API regression tests (health + voice token)
import os
import pytest
import requests
from dotenv import dotenv_values

BASE_URL = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
API_KEY = dotenv_values("/app/backend/.env").get("ELEVENLABS_API_KEY", "")


@pytest.fixture
def s():
    return requests.Session()


# Health
def test_health(s):
    r = s.get(f"{BASE_URL}/api/health", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert d["configured"] is True
    assert "problem" not in d


# Voice token
def test_voice_token(s):
    r = s.get(f"{BASE_URL}/api/get-voice-token", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d["signedUrl"], str)
    assert d["signedUrl"].startswith("wss://")
    assert d["token"] == d["signedUrl"]
    assert API_KEY and API_KEY not in r.text


def test_voice_token_unique_per_call(s):
    a = s.get(f"{BASE_URL}/api/get-voice-token", timeout=30).json()["signedUrl"]
    b = s.get(f"{BASE_URL}/api/get-voice-token", timeout=30).json()["signedUrl"]
    assert a != b


# Root page served
def test_root_page(s):
    r = s.get(f"{BASE_URL}/", timeout=30)
    assert r.status_code == 200
    assert 'data-testid="call-toggle-button"' in r.text


def test_unknown_api_path(s):
    r = s.get(f"{BASE_URL}/api/does-not-exist", timeout=30)
    # Express SPA catch-all returns index.html for unknown paths
    print("unknown api status:", r.status_code, r.headers.get("content-type"))
    assert r.status_code in (200, 404)
