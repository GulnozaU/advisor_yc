"""Composio wrapper for Gmail + Google Calendar (Composio-managed Google auth)."""
import os
from datetime import timedelta
from typing import List, Tuple

from starlette.concurrency import run_in_threadpool

from advisor.db import db, now, now_iso
from advisor.llm import logged
from advisor.types import Event, Message, Thread

TOOLKITS = ("gmail", "googlecalendar")
_client = None


def client():
    global _client
    if _client is None:
        from composio import Composio
        if not os.environ.get("COMPOSIO_API_KEY"):
            raise RuntimeError("COMPOSIO_API_KEY is not set")
        _client = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
    return _client


def _get(obj, *names, default=None):
    for n in names:
        v = obj.get(n) if isinstance(obj, dict) else getattr(obj, n, None)
        if v not in (None, ""):
            return v
    return default


async def _auth_config(toolkit: str) -> str:
    doc = await db.integration_configs.find_one({"toolkit": toolkit})
    if doc:
        return doc["auth_config_id"]
    cfg = await run_in_threadpool(client().auth_configs.create, toolkit=toolkit,
                                  options={"type": "use_composio_managed_auth", "name": f"Advisor on Call {toolkit}"})
    await db.integration_configs.insert_one({"toolkit": toolkit, "auth_config_id": cfg.id, "created_at": now_iso()})
    return cfg.id


async def connect_link(uid: str, toolkit: str, callback_url: str) -> str:
    cfg = await _auth_config(toolkit)
    req = await logged(f"composio.link.{toolkit}", run_in_threadpool(client().connected_accounts.link, uid, cfg, callback_url=callback_url))
    return req.redirect_url


async def status(uid: str) -> dict:
    res = await logged("composio.accounts", run_in_threadpool(client().connected_accounts.list, user_ids=[uid]))
    out = {t: False for t in TOOLKITS}
    for acc in _get(res, "items", default=[]) or []:
        slug = _get(_get(acc, "toolkit", default={}), "slug", default="")
        if slug in out and str(_get(acc, "status", default="")).upper() == "ACTIVE":
            out[slug] = True
    return out


async def run(uid: str, slug: str, args: dict) -> dict:
    res = await logged(f"composio.{slug}", run_in_threadpool(
        client().tools.execute, slug, args, user_id=uid, dangerously_skip_version_check=True))
    if not _get(res, "successful", default=False):
        raise RuntimeError(f"{slug} failed: {str(_get(res, 'error', default='unknown'))[:160]}")
    return _get(res, "data", default={}) or {}


def _cat(labels: List[str]):
    for l in labels or []:
        if l.startswith("CATEGORY_") and l != "CATEGORY_PERSONAL":
            return l.replace("CATEGORY_", "").capitalize()
    return None


async def fetch_threads(uid: str, me: str) -> List[Thread]:
    since = (now() - timedelta(days=15)).strftime("%Y/%m/%d")
    data = await run(uid, "GMAIL_FETCH_EMAILS", {"query": f"after:{since}", "max_results": 100, "include_payload": True, "verbose": True})
    grouped = {}
    for m in _get(data, "messages", default=[]) or []:
        labels = _get(m, "labelIds", "label_ids", default=[]) or []
        headers = {h.get("name", "").lower(): h.get("value", "") for h in (_get(_get(m, "payload", default={}) or {}, "headers", default=[]) or [])}
        tid = _get(m, "threadId", "thread_id")
        msg = Message(id=_get(m, "messageId", "id"), sender=_get(m, "sender", default=headers.get("from", "")),
                      to=[x.strip() for x in (_get(m, "to", default=headers.get("to", "")) or "").split(",") if x.strip()],
                      cc=[x.strip() for x in headers.get("cc", "").split(",") if x.strip()],
                      at=_get(m, "messageTimestamp", default=now_iso()).replace("Z", "+00:00"),
                      text=(_get(m, "messageText", "preview", default="") or "")[:4000],
                      sent_by_me="SENT" in labels or me in (_get(m, "sender", default="") or "").lower())
        g = grouped.setdefault(tid, {"id": tid, "subject": _get(m, "subject", default=headers.get("subject", "")), "category": _cat(labels),
                                     "list_unsubscribe": "list-unsubscribe" in headers, "messages": []})
        g["messages"].append(msg)
    threads = []
    for g in grouped.values():
        g["messages"].sort(key=lambda x: x.at)
        threads.append(Thread(**g))
    return threads


async def fetch_events(uid: str, advisor_calendar: str = None) -> List[Event]:
    data = await run(uid, "GOOGLECALENDAR_EVENTS_LIST", {
        "calendar_id": "primary", "time_min": (now() - timedelta(days=15)).isoformat(), "time_max": (now() + timedelta(days=14)).isoformat(),
        "single_events": True, "order_by": "startTime", "max_results": 250})
    out = []
    for e in _get(data, "items", default=[]) or []:
        if advisor_calendar and _get(_get(e, "organizer", default={}), "email") == advisor_calendar:
            continue
        start, end = _get(e, "start", default={}), _get(e, "end", default={})
        atts = _get(e, "attendees", default=[]) or []
        me_att = next((a for a in atts if a.get("self")), {})
        out.append(Event(id=e["id"], title=_get(e, "summary", default="(no title)"),
                         start=_get(start, "dateTime", default=(_get(start, "date", default="") + "T00:00:00+00:00")),
                         end=_get(end, "dateTime", default=(_get(end, "date", default="") + "T00:00:00+00:00")),
                         attendees=[a.get("email", "") for a in atts], recurring=bool(_get(e, "recurringEventId")),
                         all_day="date" in start and "dateTime" not in start, declined=me_att.get("responseStatus") == "declined",
                         focus=_get(e, "eventType") in ("focusTime", "outOfOffice")))
    return out


async def create_draft(uid: str, thread_id: str, to: str, cc: List[str], body: str) -> str:
    data = await run(uid, "GMAIL_CREATE_EMAIL_DRAFT", {"thread_id": thread_id, "recipient_email": to, "cc": cc, "subject": "", "body": body, "is_html": False})
    return str(_get(data, "id", "draft_id", default=_get(_get(data, "response_data", default={}) or {}, "id", default="")))


async def send_draft(uid: str, draft_id: str) -> None:
    await run(uid, "GMAIL_SEND_DRAFT", {"draft_id": draft_id})


def participants(t: Thread, me: str) -> Tuple[str, List[str]]:
    from advisor.pipeline import email_of
    people = []
    for m in t.messages:
        for a in [m.sender, *m.to, *m.cc]:
            e = email_of(a)
            if e and e != me and e not in people:
                people.append(e)
    last_in = next((email_of(m.sender) for m in reversed(t.messages) if not m.sent_by_me), people[0] if people else "")
    return last_in, [p for p in people if p != last_in]
