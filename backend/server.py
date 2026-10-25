import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).parent / ".env")

try:  # launched as `backend.server` (the default)
    from backend.clerk_auth import clerk_router, require_user
except ModuleNotFoundError:  # launched from inside backend/ as `server`
    from clerk_auth import clerk_router, require_user

from advisor import service as advisor_service
from advisor.db import ensure_indexes
from advisor.routes import router as advisor_router

db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
app = FastAPI()
api = APIRouter(prefix="/api")

Goal = Literal["raise", "first_customers", "revenue", "ship", "hire"]
PType = Literal["send", "meet", "decide", "learn"]
GOAL_LABELS = {"raise": "Raise", "first_customers": "First customers", "revenue": "Revenue", "ship": "Ship", "hire": "Hire"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    company: str = Field(min_length=1, max_length=80)
    one_liner: str = Field(default="", max_length=200)
    website: str = Field(default="", max_length=200)
    goal: Goal


class Profile(ProfileIn):
    user_id: str
    onboarded: bool = True
    created_at: str


class PriorityIn(BaseModel):
    type: PType
    action: str = Field(min_length=1, max_length=200)
    who: str = Field(default="", max_length=120)
    reason: str = Field(default="", max_length=400)
    deadline: Optional[str] = None


class PriorityPatch(BaseModel):
    type: Optional[PType] = None
    action: Optional[str] = Field(default=None, min_length=1, max_length=200)
    who: Optional[str] = Field(default=None, max_length=120)
    reason: Optional[str] = Field(default=None, max_length=400)
    deadline: Optional[str] = None
    status: Optional[Literal["open", "done", "dismissed"]] = None


class Priority(PriorityIn):
    id: str
    user_id: str
    rank: int
    status: Literal["open", "done", "dismissed"] = "open"
    sample: bool = False
    created_at: str
    closed_at: Optional[str] = None


class ReorderIn(BaseModel):
    ids: List[str]


class CallIn(BaseModel):
    started_at: str
    duration_sec: int = Field(ge=0, le=6 * 3600)
    priority_ids: List[str] = []


class Call(BaseModel):
    id: str
    user_id: str
    started_at: str
    duration_sec: int
    priorities: List[dict]


def sample_priorities(user_id: str) -> List[Priority]:
    t = now()
    rows = [
        ("send", "Send the investor update to your angels", "Your angel investors", "It's been 6 weeks since the last one, and a short update keeps them warm before you raise.", 1),
        ("meet", "Book 3 customer discovery calls", "Recent trial sign-ups", "Five people signed up last week and nobody has talked to them yet.", 2),
        ("decide", "Pick the pricing for the launch", "You and your co-founder", "The launch page can't go live until a price is on it.", 4),
    ]
    return [
        Priority(id=new_id(), user_id=user_id, type=ty, action=a, who=w, reason=r,
                 deadline=(t + timedelta(days=d)).isoformat(), rank=i, sample=True, created_at=t.isoformat())
        for i, (ty, a, w, r, d) in enumerate(rows)
    ]


async def get_profile(user_id: str) -> Optional[Profile]:
    doc = await db.profiles.find_one({"user_id": user_id}, {"_id": 0})
    return Profile(**doc) if doc else None


async def open_priorities(user_id: str) -> List[Priority]:
    docs = await db.priorities.find({"user_id": user_id, "status": "open"}, {"_id": 0}).sort("rank", 1).to_list(200)
    return [Priority(**d) for d in docs]


@api.get("/health")
async def health():
    return {"status": "ok", "voice_configured": bool(os.environ.get("ELEVENLABS_API_KEY") and os.environ.get("ELEVENLABS_AGENT_ID"))}


@api.get("/me")
async def me(user: dict = Depends(require_user)):
    profile = await get_profile(user["user_id"])
    return profile.model_dump() if profile else {"user_id": user["user_id"], "onboarded": False}


@api.put("/me", response_model=Profile)
async def save_me(body: ProfileIn, user: dict = Depends(require_user)):
    uid = user["user_id"]
    existing = await get_profile(uid)
    profile = Profile(**body.model_dump(), user_id=uid, created_at=existing.created_at if existing else now().isoformat())
    await db.profiles.update_one({"user_id": uid}, {"$set": profile.model_dump()}, upsert=True)
    if not existing and await db.priorities.count_documents({"user_id": uid}) == 0:
        await db.priorities.insert_many([p.model_dump() for p in sample_priorities(uid)])
    return profile


@api.get("/priorities", response_model=List[Priority])
async def list_priorities(status: Literal["open", "closed"] = "open", user: dict = Depends(require_user)):
    if status == "open":
        return await open_priorities(user["user_id"])
    docs = await db.priorities.find({"user_id": user["user_id"], "status": {"$in": ["done", "dismissed"]}}, {"_id": 0}).sort("closed_at", -1).to_list(200)
    return [Priority(**d) for d in docs]


@api.post("/priorities", response_model=Priority)
async def create_priority(body: PriorityIn, user: dict = Depends(require_user)):
    uid = user["user_id"]
    last = await db.priorities.find_one({"user_id": uid, "status": "open"}, {"_id": 0, "rank": 1}, sort=[("rank", -1)])
    p = Priority(**body.model_dump(), id=new_id(), user_id=uid, rank=(last["rank"] + 1) if last else 0, created_at=now().isoformat())
    await db.priorities.insert_one(p.model_dump())
    return p


@api.post("/priorities/reorder")
async def reorder(body: ReorderIn, user: dict = Depends(require_user)):
    for i, pid in enumerate(body.ids):
        await db.priorities.update_one({"id": pid, "user_id": user["user_id"]}, {"$set": {"rank": i}})
    return {"ok": True}


@api.patch("/priorities/{pid}", response_model=Priority)
async def update_priority(pid: str, body: PriorityPatch, user: dict = Depends(require_user)):
    changes = body.model_dump(exclude_unset=True)
    if "status" in changes:
        changes["closed_at"] = None if changes["status"] == "open" else now().isoformat()
        if changes["status"] == "open":
            last = await db.priorities.find_one({"user_id": user["user_id"], "status": "open"}, {"_id": 0, "rank": 1}, sort=[("rank", -1)])
            changes["rank"] = (last["rank"] + 1) if last else 0
    doc = await db.priorities.find_one_and_update({"id": pid, "user_id": user["user_id"]}, {"$set": changes},
                                                  projection={"_id": 0}, return_document=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return Priority(**doc)


@api.delete("/priorities/{pid}")
async def delete_priority(pid: str, user: dict = Depends(require_user)):
    if (await db.priorities.delete_one({"id": pid, "user_id": user["user_id"]})).deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api.get("/calls", response_model=List[Call])
async def list_calls(user: dict = Depends(require_user)):
    docs = await db.calls.find({"user_id": user["user_id"]}, {"_id": 0}).sort("started_at", -1).to_list(200)
    return [Call(**d) for d in docs]


@api.post("/calls", response_model=Call)
async def save_call(body: CallIn, user: dict = Depends(require_user)):
    uid = user["user_id"]
    docs = await db.priorities.find({"user_id": uid, "id": {"$in": body.priority_ids}}, {"_id": 0, "id": 1, "action": 1, "type": 1}).to_list(50)
    docs += await db.items.find({"uid": uid, "id": {"$in": body.priority_ids}}, {"_id": 0, "id": 1, "action": 1, "kind": 1}).to_list(50)
    by_id = {d["id"]: d for d in docs}
    call = Call(id=new_id(), user_id=uid, started_at=body.started_at, duration_sec=body.duration_sec,
                priorities=[by_id[i] for i in body.priority_ids if i in by_id])
    await db.calls.insert_one(call.model_dump())
    return call


def due_text(deadline: Optional[str]) -> str:
    if not deadline:
        return "no deadline"
    days = (datetime.fromisoformat(deadline) - now()).total_seconds() / 86400
    if days < 0:
        return "overdue"
    return "due today" if days < 1 else f"due in {round(days)} days"


def call_context(profile: Optional[Profile], items: List[Priority]) -> dict:
    top = items[:5]
    lines = [f"{i + 1}. [{p.type}] {p.action}" + (f" (for {p.who})" if p.who else "") + f", {due_text(p.deadline)}. Why: {p.reason or 'not given'}"
             for i, p in enumerate(top)]
    return {
        "founder_name": profile.name if profile else "there",
        "company": profile.company if profile else "your company",
        "one_liner": (profile.one_liner if profile else "") or "not given",
        "goal": GOAL_LABELS[profile.goal] if profile else "not set",
        "top_priority": top[0].action if top else "nothing on the list yet",
        "top_priority_reason": (top[0].reason or "not given") if top else "the list is empty",
        "priorities": "\n".join(lines) or "No open priorities.",
    }


@api.get("/voice-token")
async def voice_token(user: dict = Depends(require_user)):
    key, agent = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_AGENT_ID")
    if not key or not agent:
        raise HTTPException(status_code=500, detail="Voice is not configured yet.")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                             params={"agent_id": agent}, headers={"xi-api-key": key})
    if r.status_code != 200:
        hint = {401: "API key rejected. It needs the ElevenAgents Write permission.", 404: "Agent not found. Check the agent ID."}
        raise HTTPException(status_code=502, detail=hint.get(r.status_code, "Could not reach the voice service."))
    signed = r.json()["signed_url"]
    if await advisor_service.mode_of(user["user_id"]) != "manual":
        ctx = await advisor_service.call_context(user["user_id"])
        ids = ctx.pop("top_ids")
        keywords = ctx.pop("keywords")
        return {"signedUrl": signed, "token": signed, "dynamicVariables": ctx, "priorityIds": ids, "keywords": keywords, "advisor": True}
    items = await open_priorities(user["user_id"])
    profile = await get_profile(user["user_id"])
    ctx = call_context(profile, items)
    ctx.update(opening_line=f"Hi {ctx['founder_name']}, let's start with {ctx['top_priority']}.", brief=ctx["priorities"],
               tone_note="none")
    return {"signedUrl": signed, "token": signed, "dynamicVariables": ctx, "priorityIds": [p.id for p in items[:5]], "advisor": False}


app.include_router(api)
app.include_router(clerk_router)
app.include_router(advisor_router)


@app.on_event("startup")
async def _indexes():
    await ensure_indexes()
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])
