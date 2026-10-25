from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Kind = Literal["send", "meet", "decide", "learn"]
Source = Literal["thread", "calendar", "market", "playbook"]
Counterparty = Literal["investor_active", "investor_prospect", "customer", "prospect", "partner", "candidate",
                       "advisor", "vendor", "team", "personal", "noise"]


class Label(BaseModel):
    counterparty_type: Counterparty
    warmth: Literal["warm", "cold"]
    open_loop: Literal["none", "owed_reply", "owed_deliverable", "awaiting_them"]
    ask: str = Field(max_length=120)
    promised_date: Optional[str] = None
    effort: Literal[5, 15, 30, 60]
    evidence: str


class Message(BaseModel):
    id: str
    sender: str
    to: List[str] = []
    cc: List[str] = []
    at: str
    text: str
    sent_by_me: bool = False


class Thread(BaseModel):
    id: str
    subject: str
    category: Optional[str] = None
    list_unsubscribe: bool = False
    messages: List[Message]
    label: Optional[Label] = None  # fixture gold label; live threads are labeled by Claude


class Event(BaseModel):
    id: str
    title: str
    start: str
    end: str
    attendees: List[str] = []
    recurring: bool = False
    all_day: bool = False
    declined: bool = False
    focus: bool = False


class Item(BaseModel):
    id: str
    uid: str
    ref_key: str
    kind: Kind
    action: str
    target: str = ""
    why: str = ""
    evidence: str = ""
    source: Source
    priority: float
    deadline: Optional[str] = None
    effort_min: int = 15
    draft_id: Optional[str] = None
    status: Literal["open", "done", "dismissed"] = "open"
    score_parts: dict = {}
    thread_id: Optional[str] = None
    link: Optional[str] = None
    created_at: str
    updated_at: str
