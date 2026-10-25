"""Guest access for the public demo: a random httpOnly cookie, demo data only. Signed-in users still use Clerk."""
import re
import secrets

from fastapi import HTTPException, Request, Response

from advisor import service
from advisor.db import db, now_iso

try:
    from backend.clerk_auth import require_user
except ModuleNotFoundError:
    from clerk_auth import require_user

COOKIE = "aoc_guest"
GUEST_RE = re.compile(r"^guest_[a-f0-9]{32}$")


async def require_member(request: Request) -> dict:
    """Clerk user when a session token is sent, otherwise a known guest cookie."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and len(auth) > 20 or request.cookies.get("__session"):
        return require_user(request)
    gid = request.cookies.get(COOKIE, "")
    if GUEST_RE.match(gid) and await db.guests.find_one({"uid": gid}):
        return {"user_id": gid, "guest": True}
    raise HTTPException(status_code=401, detail="Not signed in")


async def start_guest(request: Request, response: Response) -> dict:
    gid = request.cookies.get(COOKIE, "")
    if not (GUEST_RE.match(gid) and await db.guests.find_one({"uid": gid})):
        gid = "guest_" + secrets.token_hex(16)
        await db.guests.insert_one({"uid": gid, "created_at": now_iso()})
        await db.profiles.insert_one({"user_id": gid, "name": "Mira Chen", "company": "Northwind", "one_liner": "Analytics for logistics teams",
                                      "website": "northwind.example.com", "goal": "raise", "onboarded": True, "created_at": now_iso(),
                                      "data_mode": "demo", "guest": True})
        await service.reset_demo(gid)
        await service.sync(gid)
    response.set_cookie(COOKIE, gid, max_age=7 * 86400, httponly=True, secure=True, samesite="lax", path="/")
    return {"guest": True}


def end_guest(response: Response) -> dict:
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
