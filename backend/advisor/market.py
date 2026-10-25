"""Competitors via Exa: discovery, overlap rating, pricing/hero snapshots, crisis tone."""
import hashlib
import json
import os
import re
from typing import List, Optional

import httpx

from advisor.db import db, new_id, now, now_iso
from advisor.llm import LABEL_MODEL, UNTRUSTED, claude, logged, summarize_change

AGGREGATORS = ("g2.com", "capterra.com", "crunchbase.com", "wikipedia.org", "linkedin.com", "trustradius.com",
               "getapp.com", "producthunt.com", "softwareadvice.com", "medium.com", "youtube.com", "reddit.com",
               "github.com", "dev.to", "vercel.app", "netlify.app", "npmjs.com", "wiki", "pcmag.com", "forbes.com", "nerdwallet.com")


async def _exa(path: str, body: dict) -> dict:
    key = os.environ.get("EXA_API_KEY")
    if not key:
        raise RuntimeError("EXA_API_KEY is not set")

    async def go():
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post("https://api.exa.ai" + path, headers={"x-api-key": key}, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"Exa {r.status_code}: {r.text[:160]}")
        return r.json()
    return await logged(f"exa{path.replace('/', '.')}", go())


def _domain(url: str) -> str:
    return re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0].lower())


async def find_candidates(website: str, one_liner: str) -> List[dict]:
    if not os.environ.get("EXA_API_KEY"):
        raise RuntimeError("EXA_API_KEY is not set")
    own = _domain(website)
    seen, out = set(), []
    calls = [("/findSimilar", {"url": f"https://{own}", "numResults": 10, "excludeSourceDomain": True, "excludeDomains": list(AGGREGATORS)})] if own else []
    calls += [("/search", {"query": q, "numResults": 8, "type": "auto", "excludeDomains": list(AGGREGATORS)})
              for q in (f"{one_liner} software company", f"alternatives to a startup that does {one_liner}")]
    for path, body in calls:
        try:
            res = await _exa(path, body)
        except Exception:
            continue
        for r in res.get("results", []):
            d = _domain(r.get("url", ""))
            if d and d != own and d not in seen and not any(a in d for a in AGGREGATORS):
                seen.add(d)
                out.append({"domain": d, "name": (r.get("title") or d).replace("\xa0", " ").split("|")[0].split(" - ")[0].strip()[:60], "url": r.get("url")})
    return out[:10]


async def rate_overlap(founder: dict, comp: dict) -> dict:
    raw = await claude("anthropic.beta", LABEL_MODEL, UNTRUSTED + "\nReply JSON only: {icp_overlap, job_overlap, reason}. Each overlap is 0, 0.33, 0.67 or 1.",
                       f"Founder company: {founder.get('company')} — {founder.get('one_liner')}\nCompetitor:\n<untrusted>{comp['name']} ({comp['domain']}): {comp.get('hero', '')[:800]}</untrusted>", 150)
    j = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    return {"icp_overlap": float(j["icp_overlap"]), "job_overlap": float(j["job_overlap"]), "reason": str(j.get("reason", ""))[:160]}


async def _text(url: str) -> Optional[str]:
    res = await _exa("/contents", {"urls": [url], "text": {"maxCharacters": 4000}})
    rs = res.get("results", [])
    return re.sub(r"\s+", " ", rs[0].get("text", "")).strip() if rs else None


async def diff_competitors(uid: str) -> int:
    """Snapshot pricing + hero of confirmed competitors; a changed hash creates a market item."""
    created = 0
    async for c in db.competitors.find({"uid": uid, "confirmed": True}, {"_id": 0}).sort("beta", -1).limit(5):
        for kind, url in (("pricing", f"https://{c['domain']}/pricing"), ("hero", f"https://{c['domain']}")):
            try:
                text = await _text(url)
            except Exception:
                continue
            if not text:
                continue
            h = hashlib.sha256(text.encode()).hexdigest()
            last = await db.snapshots.find_one({"uid": uid, "domain": c["domain"], "kind": kind}, sort=[("fetched_at", -1)])
            await db.snapshots.insert_one({"uid": uid, "domain": c["domain"], "kind": kind, "content_hash": h, "text": text[:4000], "fetched_at": now_iso()})
            if kind == "hero":
                await db.competitors.update_one({"uid": uid, "domain": c["domain"]}, {"$set": {"hero": text[:500]}})
            if last and last["content_hash"] != h:
                fact = await summarize_change(last["text"], text)
                await add_market_event(uid, c, f"{c['name']}: {fact}", 3, "pricing" if kind == "pricing" else "launch", url)
                created += 1
    return created


async def add_market_event(uid: str, comp: dict, fact: str, magnitude: int, kind: str, url: str = None) -> dict:
    ev = {"id": new_id()[:10], "uid": uid, "name": comp["name"], "domain": comp["domain"], "fact": fact, "beta": comp.get("beta", 0.5),
          "magnitude": magnitude, "kind": kind, "url": url, "created_at": now_iso()}
    await db.market_events.insert_one(dict(ev))
    return ev


async def crisis_note(uid: str) -> Optional[str]:
    """Once per day: one-line tone guidance or None."""
    today = now().date().isoformat()
    doc = await db.crisis.find_one({"uid": uid, "day": today})
    if doc:
        return doc.get("note")
    note = None
    try:
        res = await _exa("/search", {"query": "major global market crash or geopolitical crisis this week", "numResults": 5, "type": "auto",
                                     "startPublishedDate": (now().replace(hour=0) .isoformat())[:10] + "T00:00:00Z", "contents": {"highlights": True}})
        heads = "\n".join(r.get("title", "") for r in res.get("results", []))
        if heads:
            raw = await claude("anthropic.crisis", LABEL_MODEL, UNTRUSTED + "\nIf these headlines show a major market-wide or geopolitical crisis, reply with one line of tone guidance for founder emails. Otherwise reply exactly NONE.",
                               f"<untrusted>{heads}</untrusted>", 60)
            note = None if raw.strip().upper().startswith("NONE") else raw.strip()[:160]
    except Exception:
        pass
    await db.crisis.update_one({"uid": uid, "day": today}, {"$set": {"note": note}}, upsert=True)
    return note
