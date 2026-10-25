import os
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


async def ensure_indexes():
    await db.items.create_index([("uid", 1), ("ref_key", 1)], unique=True)
    await db.label_cache.create_index([("uid", 1), ("thread_id", 1), ("last_message_id", 1), ("prompt_version", 1)], unique=True)
    await db.competitors.create_index([("uid", 1), ("domain", 1)], unique=True)
    await db.sends.create_index([("uid", 1), ("draft_id", 1)], unique=True)
    await db.memories.create_index([("uid", 1), ("source", 1), ("ref_id", 1)], unique=True)
    await db.memories.create_index([("summary", "text"), ("evidence", "text")], name="memories_text")
