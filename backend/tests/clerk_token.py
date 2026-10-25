"""Test helper: prints a fresh Clerk session token for a test user. Usage: python tests/clerk_token.py founder|second [ticket]"""
import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
USERS = {"founder": "user_3LC78KNyemxv9VfZ0byoe7dJgXw", "second": "user_3LC78OvVhkrq5iy0YjvAjt3QdYz"}


def bapi(path, body):
    req = urllib.request.Request("https://api.clerk.com/v1" + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + os.environ["CLERK_SECRET_KEY"], "Content-Type": "application/json", "User-Agent": "emergent-test"})
    return json.load(urllib.request.urlopen(req))


if __name__ == "__main__":
    uid = USERS[sys.argv[1]]
    if len(sys.argv) > 2:
        print(bapi("/sign_in_tokens", {"user_id": uid, "expires_in_seconds": 900})["token"])
    else:
        s = bapi("/sessions", {"user_id": uid})
        print(bapi(f"/sessions/{s['id']}/tokens", {"expires_in_seconds": 3600})["jwt"])
