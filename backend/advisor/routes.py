from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from advisor import google, market, service
from advisor.db import db, now_iso


router = APIRouter(prefix="/api/advisor")


async def member(request: Request) -> dict:
    from guest import require_member
    return await require_member(request)


def uid_of(user: dict = Depends(member)) -> str:
    return user["user_id"]


def real_user(user: dict = Depends(member)) -> str:
    if user.get("guest"):
        raise HTTPException(status_code=403, detail="Sign up to connect your own Gmail and Calendar.")
    return user["user_id"]


def _public(items, n=None):
    return [i.model_dump(exclude={"uid"}) for i in (items[:n] if n else items)]


def _fail(e: Exception, what: str):
    raise HTTPException(status_code=424, detail=f"{what} failed. {str(e)[:140]}")


class ModeIn(BaseModel):
    mode: Literal["manual", "demo", "live"]


@router.post("/mode")
async def set_mode(body: ModeIn, user: dict = Depends(member)):
    uid = user["user_id"]
    if user.get("guest") and body.mode != "demo":
        raise HTTPException(status_code=403, detail="Sign up to use your own list or Gmail.")
    if not await db.profiles.find_one({"user_id": uid}):
        raise HTTPException(status_code=400, detail="Finish onboarding first.")
    await db.profiles.update_one({"user_id": uid}, {"$set": {"data_mode": body.mode}})
    if body.mode == "demo":
        await service.reset_demo(uid)
    return {"mode": body.mode, "items": _public(await service.sync(uid), 5)}


@router.get("/items")
async def items(uid: str = Depends(uid_of)):
    mode = await service.mode_of(uid)
    ranked = await service.ranked(uid) if mode != "manual" else []
    closed = [d async for d in db.items.find({"uid": uid, "status": {"$ne": "open"}}, {"_id": 0, "uid": 0}).sort("updated_at", -1).limit(30)]
    return {"mode": mode, "top": _public(ranked, 5), "rest": _public(ranked[5:]), "closed": closed}


@router.post("/sync")
async def sync(uid: str = Depends(uid_of)):
    try:
        ranked = await service.sync(uid, fetch=True)
    except Exception as e:
        _fail(e, "Sync")
    return {"top": _public(ranked, 5)}


class StatusIn(BaseModel):
    status: Literal["open", "done", "dismissed"]


@router.post("/items/{item_id}/status")
async def item_status(item_id: str, body: StatusIn, uid: str = Depends(uid_of)):
    if not await service.set_status(uid, item_id, body.status):
        raise HTTPException(status_code=404, detail="Not found")
    return {"top": _public(await service.ranked(uid), 5)}


class ReasonIn(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


@router.post("/items/{item_id}/reprioritize")
async def reprioritize(item_id: str, body: ReasonIn, uid: str = Depends(uid_of)):
    ranked = await service.reprioritize(uid, item_id, body.reason)
    if ranked is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"top": _public(ranked, 5)}


@router.post("/items/{item_id}/draft")
async def draft(item_id: str, uid: str = Depends(uid_of)):
    try:
        d = await service.make_draft(uid, item_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _fail(e, "Drafting")
    return {k: v for k, v in d.items() if k != "uid"}


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, uid: str = Depends(uid_of)):
    d = await db.drafts.find_one({"uid": uid, "id": draft_id}, {"_id": 0, "uid": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Not found")
    return d


@router.post("/drafts/{draft_id}/send")
async def send(draft_id: str, uid: str = Depends(uid_of)):
    try:
        result = await service.send(uid, draft_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _fail(e, "Sending")
    return {"result": result, "top": _public(await service.ranked(uid), 5)}


class QueryIn(BaseModel):
    query: str = Field(min_length=1, max_length=300)


@router.post("/lookup")
async def lookup(body: QueryIn, uid: str = Depends(uid_of)):
    return await service.lookup(uid, body.query)


class EventIn(BaseModel):
    kind: Literal["price_cut", "investor_email"]


@router.post("/demo/event")
async def demo_event(body: EventIn, uid: str = Depends(uid_of)):
    if await service.mode_of(uid) != "demo":
        raise HTTPException(status_code=400, detail="Turn on the demo story first.")
    msg = await service.demo_event(uid, body.kind)
    return {"event": msg, "top": _public(await service.ranked(uid), 5)}


@router.get("/google/status")
async def google_status(uid: str = Depends(real_user)):
    try:
        return await google.status(uid)
    except Exception as e:
        _fail(e, "Checking Google connection")


class ConnectIn(BaseModel):
    toolkit: Literal["gmail", "googlecalendar"]


@router.post("/google/connect")
async def google_connect(body: ConnectIn, request: Request, uid: str = Depends(real_user)):
    origin = request.headers.get("origin") or ""
    try:
        url = await google.connect_link(uid, body.toolkit, f"{origin}/connections?connected={body.toolkit}")
    except Exception as e:
        _fail(e, "Starting the Google connection")
    return {"redirect_url": url}


@router.get("/competitors")
async def competitors(uid: str = Depends(uid_of)):
    return [d async for d in db.competitors.find({"uid": uid}, {"_id": 0, "uid": 0}).sort("beta", -1)]


@router.post("/competitors/find")
async def find_competitors(uid: str = Depends(real_user)):
    p = await db.profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    try:
        cands = await market.find_candidates(p.get("website", ""), p.get("one_liner") or p.get("company", ""))
    except Exception as e:
        _fail(e, "Finding competitors")
    for c in cands:
        await db.competitors.update_one({"uid": uid, "domain": c["domain"]},
                                        {"$setOnInsert": {**c, "uid": uid, "confirmed": False, "beta": 0, "created_at": now_iso()}}, upsert=True)
    return await competitors(uid)


class ConfirmIn(BaseModel):
    domain: str
    confirmed: bool


@router.post("/competitors/confirm")
async def confirm_competitor(body: ConfirmIn, uid: str = Depends(real_user)):
    c = await db.competitors.find_one({"uid": uid, "domain": body.domain}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    update = {"confirmed": body.confirmed}
    if body.confirmed and not c.get("rated"):
        p = await db.profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
        try:
            r = await market.rate_overlap(p, c)
            update.update(r, beta=round(r["icp_overlap"] * r["job_overlap"], 3), rated=True)
        except Exception:
            update.update(beta=0.5)
    await db.competitors.update_one({"uid": uid, "domain": body.domain}, {"$set": update})
    return await competitors(uid)
