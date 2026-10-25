# Clerk backend API helpers for tests: mint session JWTs and sign-in tickets (never prints the secret)
import uuid
import requests
from dotenv import dotenv_values

_SK = dotenv_values("/app/backend/.env").get("CLERK_SECRET_KEY", "")
CLERK = "https://api.clerk.com/v1"
H = {"Authorization": f"Bearer {_SK}", "User-Agent": "emergent-test-agent", "Content-Type": "application/json"}

FOUNDER = "user_3LC78KNyemxv9VfZ0byoe7dJgXw"
SECOND = "user_3LC78OvVhkrq5iy0YjvAjt3QdYz"


def session_token(user_id: str) -> str:
    s = requests.post(f"{CLERK}/sessions", headers=H, json={"user_id": user_id}, timeout=20)
    s.raise_for_status()
    t = requests.post(f"{CLERK}/sessions/{s.json()['id']}/tokens", headers=H, json={}, timeout=20)
    t.raise_for_status()
    return t.json()["jwt"]


def sign_in_ticket(user_id: str) -> str:
    r = requests.post(f"{CLERK}/sign_in_tokens", headers=H, json={"user_id": user_id, "expires_in_seconds": 600}, timeout=20)
    r.raise_for_status()
    return r.json()["token"]


def create_temp_user() -> str:
    email = f"tmp{uuid.uuid4().hex[:8]}+clerk_test@example.com"
    r = requests.post(f"{CLERK}/users", headers=H, json={"email_address": [email], "password": "Advisor-test-2026!xYz", "skip_password_checks": True}, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def delete_user(user_id: str):
    requests.delete(f"{CLERK}/users/{user_id}", headers=H, timeout=20)
