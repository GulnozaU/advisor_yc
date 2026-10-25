import asyncio
import os
import re
import time
from datetime import timedelta
from typing import List, Optional

from pymongo.errors import DuplicateKeyError

from advisor import fixtures, google, market, pipeline, scoring
from advisor.db import db, new_id, now, now_iso
from advisor.llm import label_thread, write_draft
from advisor.scoring_constants import PROMPT_VERSION
from advisor.types import Event, Item, Label, Thread

DEMO_CONTACTS = {"ceo@betacorp.example.com": "Sam at Beta Corp", "priya@fundx.example.com": "Priya at Fund X",
                 "dana@acme.example.com": "Dana at Acme", "tom@advisors.example.com": "Tom, your advisor",
                 "alex@seedcap.example.com": "Alex at Seed Capital"}
GOAL_MAP = {"first_customers": "first_customers"}
PLACEHOLDER = re.compile(r"\[[^\[\]\n]{1,60}\]")
STOP = {"what", "happened", "with", "the", "and", "about", "did", "does", "was", "were", "last", "month", "week", "tell",
        "how", "are", "they", "their", "them", "this", "that", "from", "for", "you", "any", "our", "who", "when", "why", "has", "have"}


async def mode_of(uid: str) -> str:
    p = await db.profiles.find_one({"user_id": uid}, {"_id": 0, "data_mode": 1})
    return (p or {}).get("data_mode", "manual")


async def founder_of(uid: str, mode: str) -> dict:
    if mode == "demo":
        return fixtures.build()["founder"]
    p = await db.profiles.find_one({"user_id": uid}, {"_id": 0}) or {}
    return {"name": p.get("name", ""), "company": p.get("company", ""), "one_liner": p.get("one_liner", ""),
            "website": p.get("website", ""), "goal": p.get("goal", "raise"), "email": p.get("gmail_address", "me@unknown")}


async def _labels_live(uid: str, threads: List[Thread]) -> dict:
    sem, out = asyncio.Semaphore(5), {}

    async def one(t: Thread):
        key = {"uid": uid, "thread_id": t.id, "last_message_id": t.messages[-1].id, "prompt_version": PROMPT_VERSION}
        hit = await db.label_cache.find_one(key, {"_id": 0, "label": 1})
        if hit:
            out[t.id] = Label(**hit["label"])
            return
        async with sem:
            try:
                lb = await label_thread(pipeline.thread_text(t))
            except Exception:
                return
        out[t.id] = lb
        try:
            await db.label_cache.insert_one({**key, "label": lb.model_dump()})
        except DuplicateKeyError:
            pass
    await asyncio.gather(*(one(t) for t in threads[:60]))
    return out


async def load_sources(uid: str, mode: str):
    if mode == "demo":
        data = fixtures.build()
        threads = [Thread(**t) for t in data["threads"]]
        threads += [Thread(**d["thread"]) async for d in db.demo_extra.find({"uid": uid}, {"_id": 0})]
        events = [Event(**e) for e in data["events"]]
        return threads, events, {t.id: t.label for t in threads if t.label}, DEMO_CONTACTS
    threads = [Thread(**d) async for d in db.threads.find({"uid": uid}, {"_id": 0, "uid": 0})]
    events = [Event(**d) async for d in db.events.find({"uid": uid}, {"_id": 0, "uid": 0})]
    kept = [t for t in threads if pipeline.keep_thread(t)]
    return threads, events, await _labels_live(uid, kept), {}


async def fetch_live(uid: str):
    conn = await google.status(uid)
    if conn["gmail"]:
        threads = await google.fetch_threads(uid, "")
        me = next((pipeline.email_of(m.sender) for t in threads for m in t.messages if m.sent_by_me), None)
        if me:
            await db.profiles.update_one({"user_id": uid}, {"$set": {"gmail_address": me}})
            for t in threads:
                for m in t.messages:
                    m.sent_by_me = m.sent_by_me or pipeline.email_of(m.sender) == me
        await db.threads.delete_many({"uid": uid})
        if threads:
            await db.threads.insert_many([{**t.model_dump(), "uid": uid} for t in threads])
    if conn["googlecalendar"]:
        events = await google.fetch_events(uid)
        await db.events.delete_many({"uid": uid})
        if events:
            await db.events.insert_many([{**e.model_dump(), "uid": uid} for e in events])
    return conn


async def sync(uid: str, fetch: bool = False) -> List[Item]:
    mode = await mode_of(uid)
    if mode == "manual":
        return []
    if mode == "live" and fetch:
        await fetch_live(uid)
        try:
            await market.diff_competitors(uid)
        except Exception:
            pass
    founder = await founder_of(uid, mode)
    threads, events, labels, contacts = await load_sources(uid, mode)
    market_events = [d async for d in db.market_events.find({"uid": uid}, {"_id": 0})]
    overrides = {d["ref_key"]: d["mult"] async for d in db.overrides.find({"uid": uid}, {"_id": 0})}
    built = pipeline.build_items(uid, founder, threads, events, labels, now(), contacts, market_events, overrides)
    existing = {d["ref_key"]: d async for d in db.items.find({"uid": uid}, {"_id": 0})}
    for it in built:
        old = existing.get(it.ref_key)
        if old:
            it.status, it.draft_id, it.created_at = old["status"], old.get("draft_id"), old["created_at"]
        await db.items.update_one({"uid": uid, "ref_key": it.ref_key}, {"$set": it.model_dump()}, upsert=True)
    fresh = {i.ref_key for i in built}
    for ref, old in existing.items():  # thread loop closed (reply sent) -> item closes itself
        if ref not in fresh and old["status"] == "open" and old["source"] in ("thread", "calendar"):
            await db.items.update_one({"uid": uid, "ref_key": ref}, {"$set": {"status": "done", "updated_at": now_iso()}})
    for m in pipeline.memories_from(threads, events, labels, contacts):
        await db.memories.update_one({"uid": uid, "source": m["source"], "ref_id": m["ref_id"]}, {"$set": {**m, "uid": uid}}, upsert=True)
    return await ranked(uid)


async def ranked(uid: str) -> List[Item]:
    items = [Item(**d) async for d in db.items.find({"uid": uid, "status": "open"}, {"_id": 0})]
    state = await db.rank_state.find_one({"uid": uid}) or {}
    out = scoring.rank(items, state.get("top", []))
    await db.rank_state.update_one({"uid": uid}, {"$set": {"top": [i.id for i in out[:5]]}}, upsert=True)
    return out


def _hours_until(iso: Optional[str]) -> str:
    if not iso:
        return "no deadline"
    h = (scoring.datetime.fromisoformat(iso) - now()).total_seconds() / 3600
    return "overdue" if h < 0 else f"due in {round(h)}h"


def opening_line(top: List[Item]) -> str:
    if not top:
        return "You're clear right now. A good moment for one deep-work block on the thing only you can do."
    t = top[0]
    offer = " Want me to draft it?" if t.source in ("thread", "calendar") else ""
    return f"{t.action}. {t.why.split('.')[0]}.{offer}"


async def brief(uid: str, top: List[Item], founder: dict, tone: Optional[str]) -> str:
    lines = [f"Founder: {founder['name']}, {founder.get('company')}: {founder.get('one_liner')}. Goal: {founder.get('goal')}."]
    lines += [f"#{n + 1} [{i.kind}/{i.source}] id={i.id} | {i.action} | why: {i.why} | evidence: \"{i.evidence[:160]}\" | {_hours_until(i.deadline)}"
              for n, i in enumerate(top[:5])]
    comps = [c async for c in db.competitors.find({"uid": uid, "confirmed": True}, {"_id": 0, "name": 1, "hero": 1}).limit(3)]
    lines += [f"Competitor {c['name']}: {(c.get('hero') or '')[:200]}" for c in comps]
    if tone:
        lines.append(f"Tone: {tone}")
    return ("<untrusted>\n" + "\n".join(lines) + "\n</untrusted>")[:10000]


async def call_context(uid: str) -> dict:
    mode = await mode_of(uid)
    top = (await sync(uid))[:5]
    founder = await founder_of(uid, mode)
    tone = await db.crisis.find_one({"uid": uid}, sort=[("day", -1)])
    tone_note = (tone or {}).get("note") or "none"
    return {"opening_line": opening_line(top), "brief": await brief(uid, top, founder, tone_note if tone_note != "none" else None),
            "founder_name": founder["name"], "goal": founder.get("goal", ""), "tone_note": tone_note,
            "top_ids": [i.id for i in top], "keywords": list({i.target.split(" at ")[0] for i in top if i.target})}


async def lookup(uid: str, query: str) -> dict:
    t0 = time.perf_counter()
    words = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", query.lower()) if w not in STOP][:8]
    facts = []
    if words:
        rx = "|".join(map(re.escape, words))
        async for d in db.items.find({"uid": uid, "$or": [{f: {"$regex": rx, "$options": "i"}} for f in ("action", "why", "evidence", "target")]},
                                     {"_id": 0, "id": 1, "action": 1, "why": 1, "status": 1, "source": 1}).limit(3):
            facts.append(f"[current item {d['id']}, {d['status']}] {d['action']}. {d['why']}")
        async for d in db.memories.find({"uid": uid, "$text": {"$search": " ".join(words)}},
                                        {"_id": 0, "summary": 1, "evidence": 1, "source": 1, "ref_id": 1, "timestamp": 1, "score": {"$meta": "textScore"}}
                                        ).sort([("score", {"$meta": "textScore"})]).limit(5):
            facts.append(f"[{d['source']} {d['ref_id']}, {d['timestamp'][:10]}] {d['summary']} Quote: \"{d['evidence'][:160]}\"")
        async for c in db.competitors.find({"uid": uid, "name": {"$regex": rx, "$options": "i"}}, {"_id": 0, "name": 1, "hero": 1}).limit(1):
            facts.append(f"[competitor {c['name']}] Positioning: {(c.get('hero') or '')[:300]}")
    facts = facts[:5]
    text = "\n".join(facts)[:2000]
    ms = round((time.perf_counter() - t0) * 1000, 1)
    await db.call_log.insert_one({"name": "rag.lookup", "ms": ms, "ok": True, "at": now_iso()})
    body = (f"<untrusted>\n{text}\n</untrusted>\nAnswer only from these facts and name the source. If they do not answer the question, say you don't have that information."
            if facts else "No matching records. Say you don't have that information; do not guess.")
    return {"result": body, "count": len(facts), "ms": ms}


async def set_status(uid: str, item_id: str, status: str):
    r = await db.items.update_one({"uid": uid, "id": item_id}, {"$set": {"status": status, "updated_at": now_iso()}})
    return r.matched_count > 0


async def reprioritize(uid: str, item_id: str, reason: str) -> List[Item]:
    item = await db.items.find_one({"uid": uid, "id": item_id}, {"_id": 0, "ref_key": 1})
    if not item:
        return None
    up = re.search(r"\b(urgent|more important|first|asap|top|priority|now)\b", reason.lower())
    await db.overrides.update_one({"uid": uid, "ref_key": item["ref_key"]},
                                  {"$set": {"mult": 2.0 if up else 0.3, "reason": reason[:200], "at": now_iso()}}, upsert=True)
    return await sync(uid)


async def make_draft(uid: str, item_id: str) -> dict:
    mode = await mode_of(uid)
    item = await db.items.find_one({"uid": uid, "id": item_id}, {"_id": 0})
    if not item or item["source"] not in ("thread", "calendar"):
        raise ValueError("Drafts are only available for email and meeting items.")
    existing = await db.drafts.find_one({"uid": uid, "item_id": item_id}, {"_id": 0})
    if existing:
        return existing
    founder = await founder_of(uid, mode)
    threads, events, _, _ = await load_sources(uid, mode)
    th = next((t for t in threads if t.id == item.get("thread_id")), None)
    if th:
        to, cc = google.participants(th, founder["email"].lower())
        text = pipeline.thread_text(th)
    else:
        ev = next((e for e in events if f"calendar:{e.id}" == item["ref_key"]), None)
        ext = [a for a in (ev.attendees if ev else []) if pipeline.domain_of(a) != founder["email"].split("@")[-1]]
        to, cc, text = (ext[0] if ext else ""), ext[1:], f"Meeting: {ev.title if ev else ''}"
    tone = (await db.crisis.find_one({"uid": uid}, sort=[("day", -1)]) or {}).get("note")
    if mode == "demo" and not os.environ.get("ANTHROPIC_API_KEY"):
        first = founder["name"].split()[0]
        body = (f"Hi {item['target'].split(' at ')[0].split(',')[0]},\n\nThanks for your patience. On your question ({item['why'].split('asked: ')[-1].split('.')[0].lower()}): "
                f"I'll have a clear answer for you today, ahead of our next conversation.\n\nBest,\n{first}\n\n[Template draft: add an Anthropic key for Claude-written drafts]")
    else:
        body = await write_draft(founder, text, item["action"], f"Context: {item['why']}", tone or "")
    gmail_id = await google.create_draft(uid, th.id if th else None, to, cc, body) if mode == "live" else None
    d = {"id": new_id(), "uid": uid, "item_id": item_id, "to": to, "cc": cc, "body": body, "thread_id": th.id if th else None,
         "gmail_draft_id": gmail_id, "mode": mode, "created_at": now_iso()}
    await db.drafts.insert_one(dict(d))
    await db.items.update_one({"uid": uid, "id": item_id}, {"$set": {"draft_id": d["id"]}})
    return d


async def send(uid: str, draft_id: str, body: Optional[str] = None) -> str:
    d = await db.drafts.find_one({"uid": uid, "id": draft_id}, {"_id": 0})
    if not d:
        raise ValueError("Draft not found.")
    if body is not None and body.strip() != d["body"].strip():
        d["body"] = body.strip()
        if d["mode"] == "live":
            old = d.get("gmail_draft_id")
            d["gmail_draft_id"] = await google.create_draft(uid, d.get("thread_id"), d["to"], d["cc"], d["body"])
            if old:
                try:
                    await google.run(uid, "GMAIL_DELETE_DRAFT", {"draft_id": old})
                except Exception:
                    pass
        await db.drafts.update_one({"uid": uid, "id": draft_id}, {"$set": {"body": d["body"], "gmail_draft_id": d.get("gmail_draft_id")}})
    if PLACEHOLDER.search(d["body"]):
        raise PermissionError("Fill in every [placeholder] before sending.")
    try:
        await db.sends.insert_one({"uid": uid, "draft_id": draft_id, "item_id": d["item_id"], "sent_at": now_iso()})
    except DuplicateKeyError:
        return "already_sent"
    try:
        if d["mode"] == "live":
            await google.send_draft(uid, d["gmail_draft_id"])
    except Exception:
        await db.sends.delete_one({"uid": uid, "draft_id": draft_id})
        raise
    await set_status(uid, d["item_id"], "done")
    return "sent" if d["mode"] == "live" else "simulated"


async def demo_event(uid: str, kind: str) -> str:
    if kind == "price_cut":
        e = fixtures.DEMO_EVENTS["price_cut"]
        await market.add_market_event(uid, {"name": e["name"], "domain": e["domain"], "beta": 1.0}, e["fact"], e["magnitude"], e["kind"])
        await sync(uid)
        return f"[EVENT] Market update: {e['fact']} This affects Sam at Beta Corp, who asked about tier 2 pricing."
    t = fixtures.DEMO_EVENTS["investor_email"]["thread"]
    t = {**t, "label": {**t["label"], "promised_date": (now() + timedelta(hours=8)).isoformat()},
         "messages": [{**m, "id": f"t-newinv-m{i}", "at": now_iso()} for i, m in enumerate(t["messages"])]}
    await db.demo_extra.update_one({"uid": uid, "thread.id": t["id"]}, {"$set": {"uid": uid, "thread": t}}, upsert=True)
    await sync(uid)
    return "[EVENT] New email: Alex at Seed Capital says IC meets tomorrow morning and asks for the data room by end of day."


async def reset_demo(uid: str):
    for col in ("items", "overrides", "market_events", "demo_extra", "drafts", "sends", "rank_state", "memories"):
        await db[col].delete_many({"uid": uid})
