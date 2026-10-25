"""Pure pipeline: prefilter, joins, item building. No I/O."""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from advisor import scoring
from advisor.types import Event, Item, Label, Thread

DROP_CATEGORIES = {"Promotions", "Social", "Updates", "Forums"}
NOREPLY = re.compile(r"(no-?reply|notifications?|calendar-notification|mailer-daemon)@", re.I)
PUBLIC_DOMAINS = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me"}
PLAYBOOK = json.loads((Path(__file__).parent.parent / "data" / "playbook.json").read_text())


def email_of(addr: str) -> str:
    m = re.search(r"<([^>]+)>", addr)
    return (m.group(1) if m else addr).strip().lower()


def domain_of(addr: str) -> str:
    return email_of(addr).split("@")[-1]


def display_name(addr: str) -> str:
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', addr)
    if m:
        return m.group(1).strip()
    local = email_of(addr).split("@")[0]
    return local.split(".")[0].capitalize()


def keep_thread(t: Thread) -> bool:
    if t.category in DROP_CATEGORIES or t.list_unsubscribe:
        return False
    inbound = [m for m in t.messages if not m.sent_by_me]
    if inbound and all(NOREPLY.search(email_of(m.sender)) for m in inbound):
        return False
    return not t.subject.lower().startswith("invitation:")


def keep_event(e: Event, my_domain: str) -> bool:
    if e.recurring or e.all_day or e.focus or e.declined:
        return False
    return any(domain_of(a) != my_domain for a in e.attendees)


def thread_text(t: Thread) -> str:
    return "\n\n".join(f"From: {m.sender}\nDate: {m.at}\n{re.sub(r'<[^>]+>', ' ', m.text)}" for m in t.messages)


def _hours(a: datetime, b: str) -> float:
    return (a - datetime.fromisoformat(b)).total_seconds() / 3600


def counterparty(t: Thread) -> str:
    inbound = [m for m in t.messages if not m.sent_by_me]
    return inbound[-1].sender if inbound else (t.messages[-1].to[0] if t.messages[-1].to else "")


def who_of(addr: str, contacts: Dict[str, str]) -> str:
    return contacts.get(email_of(addr)) or f"{display_name(addr)} at {domain_of(addr).split('.')[0].capitalize()}"


def build_items(uid: str, founder: dict, threads: List[Thread], events: List[Event], labels: Dict[str, Label],
                now: datetime, contacts: Dict[str, str], market: List[dict], overrides: Dict[str, float]) -> List[Item]:
    me = founder["email"].lower()
    my_domain = me.split("@")[-1]
    goal = founder.get("goal", "raise")
    ts = now.isoformat()
    items: List[Item] = []
    upcoming = [e for e in events if keep_event(e, my_domain) and 0 < -_hours(now, e.start) <= 72]
    by_email = {}

    for t in threads:
        if not keep_thread(t) or t.id not in labels:
            continue
        lb = labels[t.id]
        cp = counterparty(t)
        by_email[email_of(cp)] = lb.counterparty_type
        if lb.counterparty_type in ("noise", "personal", "vendor") or lb.open_loop == "none":
            continue
        last = t.messages[-1]
        if last.sent_by_me and lb.open_loop in ("owed_reply", "owed_deliverable") and not lb.promised_date:
            continue  # founder already replied: loop closed
        who = who_of(cp, contacts)
        anchor = next((m.at for m in reversed(t.messages) if (m.sent_by_me if lb.open_loop == "awaiting_them" else not m.sent_by_me)), last.at)
        deadline, prep = lb.promised_date, None
        for e in upcoming:
            if any(email_of(a) == email_of(cp) or domain_of(a) == domain_of(cp) for a in e.attendees):
                if not deadline or e.start < deadline:
                    deadline, prep = (deadline if deadline and deadline < now.isoformat() else e.start), e
        verb = {"owed_reply": f"Reply to {who}", "owed_deliverable": lb.ask, "awaiting_them": f"Nudge {who}: {lb.ask}"}[lb.open_loop]
        if prep:
            verb += f" before your {prep.title} in {max(1, round(-_hours(now, prep.start)))} hours"
        sp = scoring.score(lb.counterparty_type, goal, lb.open_loop, deadline, _hours(now, anchor), lb.effort, now)
        why = f"{who} asked: {lb.ask}." + (f" You promised it by {lb.promised_date[:10]}." if lb.promised_date else "")
        items.append(_item(uid, f"thread:{t.id}", "send", verb, who, why, lb.evidence, "thread", sp, deadline, lb.effort, ts, thread_id=t.id))

    sent = [m for t in threads for m in t.messages if m.sent_by_me]
    for e in events:
        if not keep_event(e, my_domain) or _hours(now, e.end) <= 0 or _hours(now, e.end) > 24 * 7:
            continue
        ext = [a for a in e.attendees if domain_of(a) != my_domain]
        if any(m.at > e.end and set(map(email_of, m.to)) & set(map(email_of, ext)) for m in sent):
            continue
        cp_type = by_email.get(email_of(ext[0]), "prospect")
        who = who_of(ext[0], contacts)
        sp = scoring.score(cp_type, goal, "meeting_followup", None, _hours(now, e.end), 15, now)
        items.append(_item(uid, f"calendar:{e.id}", "send", f"Follow up with {who} after the {e.title}", who,
                           f"The {e.title} ended {round(_hours(now, e.end))} hours ago and nothing has been sent since.",
                           e.title, "calendar", sp, None, 15, ts))

    for m in market:
        age = (now - datetime.fromisoformat(m["created_at"])).total_seconds() / 86400
        sp = scoring.soft_score(scoring.market_impact(m["beta"], m["magnitude"], age, m["kind"]))
        items.append(_item(uid, f"market:{m['id']}", "decide", f"Decide how to respond: {m['fact']}", m["name"], m["fact"],
                           m["fact"], "market", sp, None, 15, ts, link=m.get("url")))

    items += playbook_items(uid, founder, threads, events, by_email, now, ts)
    _join_market(items)
    for it in items:
        if it.ref_key in overrides:
            it.score_parts["override"] = overrides[it.ref_key]
            it.priority = round(it.priority * overrides[it.ref_key], 4)
    return items


def playbook_items(uid, founder, threads, events, by_email, now, ts) -> List[Item]:
    my_domain = founder["email"].split("@")[-1]
    cust = {"customer", "prospect"}
    meets = [e for e in events if keep_event(e, my_domain) and 0 < _hours(now, e.end) <= 24 * 14
             and any(by_email.get(email_of(a), "prospect") in cust for a in e.attendees if domain_of(a) != my_domain)]
    inv_out = [m for t in threads for m in t.messages if m.sent_by_me and _hours(now, m.at) <= 24 * 21
               and any(by_email.get(email_of(x)) in ("investor_active", "investor_prospect") for x in m.to)]
    open_cust = [t for t in threads if by_email.get(email_of(counterparty(t))) in cust]
    fired = {"few-customer-meetings": len(meets) < 3,
             "no-investor-outbound": founder.get("goal") == "raise" and not inv_out,
             "do-things-dont-scale": not open_cust}
    out = []
    for atom in PLAYBOOK:
        if fired.get(atom["id"]):
            sp = scoring.soft_score(1.0)
            out.append(_item(uid, f"playbook:{atom['id']}", "learn", atom["action"], "", atom["claim"], atom["trigger"],
                             "playbook", sp, None, 15, ts, link=atom["source_url"]))
    return out


def _join_market(items: List[Item]):
    for m in [i for i in items if i.source == "market"]:
        terms = [m.target.lower()] + re.findall(r"tier \d", m.why.lower())
        for t in items:
            if t.source == "thread" and any(term and term in (t.evidence + " " + t.why).lower() for term in terms):
                t.why += f" Market: {m.why}"


def _item(uid, ref, kind, action, target, why, evidence, source, sp, deadline, effort, ts, thread_id=None, link=None) -> Item:
    return Item(id=ref.replace(":", "-"), uid=uid, ref_key=ref, kind=kind, action=action, target=target, why=why,
                evidence=evidence, source=source, priority=sp["priority"], deadline=deadline, effort_min=effort,
                score_parts=sp, thread_id=thread_id, link=link, created_at=ts, updated_at=ts)


def memories_from(threads: List[Thread], events: List[Event], labels: Dict[str, Label], contacts) -> List[dict]:
    out = []
    for t in threads:
        lb = labels.get(t.id)
        if not lb or lb.counterparty_type in ("noise",) or not keep_thread(t):
            continue
        who = who_of(counterparty(t), contacts)
        out.append({"source": "thread", "ref_id": t.id, "timestamp": t.messages[-1].at,
                    "summary": f"{t.subject}: {who} ({lb.counterparty_type}). Ask: {lb.ask}. Status: {lb.open_loop}.",
                    "evidence": lb.evidence})
    for e in events:
        out.append({"source": "meeting", "ref_id": e.id, "timestamp": e.start,
                    "summary": f"Meeting '{e.title}' on {e.start[:16]} with {', '.join(e.attendees)}.", "evidence": e.title})
    return out
