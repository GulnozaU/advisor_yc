"""Starter priorities researched from the founder's own description (Exa web research + Claude)."""
import asyncio
import json
from typing import List, Literal

from pydantic import BaseModel, Field

from advisor.llm import DRAFT_MODEL, UNTRUSTED, claude
from advisor.market import _domain, _exa


class Suggestion(BaseModel):
    type: Literal["send", "meet", "decide", "learn"]
    action: str = Field(min_length=3, max_length=200)
    who: str = Field(default="", max_length=120)
    reason: str = Field(default="", max_length=400)
    due_in_days: int = Field(default=3, ge=0, le=30)


GOALS = {"raise": "raise money", "first_customers": "land first customers", "revenue": "grow revenue", "ship": "ship the product", "hire": "hire"}


async def _research(company: str, one_liner: str, website: str) -> str:
    desc = one_liner or company
    calls = [_exa("/search", {"query": f"{desc} startup market and competitors", "numResults": 5, "type": "auto",
                              "contents": {"highlights": {"numSentences": 2, "highlightsPerUrl": 1}}}),
             _exa("/search", {"query": f"how early-stage {desc} companies find their first customers", "numResults": 3, "type": "auto",
                              "contents": {"highlights": {"numSentences": 2, "highlightsPerUrl": 1}}})]
    if website:
        calls.append(_exa("/contents", {"urls": [f"https://{_domain(website)}"], "text": {"maxCharacters": 1500}}))
    lines = []
    for res in await asyncio.gather(*calls, return_exceptions=True):
        if isinstance(res, Exception):
            continue
        for r in res.get("results", []):
            snippet = " ".join(r.get("highlights") or []) or (r.get("text") or "")[:600]
            lines.append(f"- {r.get('title', '')} ({_domain(r.get('url', ''))}): {snippet}")
    return "\n".join(lines)[:6000]


async def suggest(profile: dict) -> List[Suggestion]:
    notes = await _research(profile.get("company", ""), profile.get("one_liner", ""), profile.get("website", ""))
    system = UNTRUSTED + """
You are a startup advisor. From the founder's own description and the web research, write exactly 5 concrete priorities for this week.
Each must be specific to this startup and its market (name real competitor types, customer segments or channels from the research), doable in under a day,
and ordered most important first for the founder's goal. Never invent people's names or facts about the founder; 'who' is a role or segment.
Reply with a JSON array only: [{"type": "send|meet|decide|learn", "action": "...", "who": "...", "reason": "one sentence why, citing the research", "due_in_days": 0-14}]"""
    user = (f"Founder: {profile.get('name')} at {profile.get('company')}. Description: {profile.get('one_liner') or 'not given'}. "
            f"Website: {profile.get('website') or 'none'}. Goal: {GOALS.get(profile.get('goal'), 'grow')}.\n<untrusted>\n{notes or 'No research found.'}\n</untrusted>")
    raw = await claude("anthropic.suggest", DRAFT_MODEL, system, user, 1200)
    items = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
    return [Suggestion(**i) for i in items][:5]
