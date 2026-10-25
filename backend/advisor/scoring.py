from datetime import datetime, timezone
from typing import List, Optional

from advisor import scoring_constants as C
from advisor.types import Item


def deadline_weight(deadline: Optional[str], now: datetime) -> float:
    if not deadline:
        return C.NO_DEADLINE
    hours = (datetime.fromisoformat(deadline) - now).total_seconds() / 3600
    if hours < 0:
        return C.OVERDUE
    for limit, w in C.DEADLINE_BUCKETS:
        if hours < limit:
            return w
    return C.NO_DEADLINE


def lateness(hours_waiting: float, median_gap_h: Optional[float]) -> float:
    gap = median_gap_h or C.LATENESS_FALLBACK_H
    return max(0.0, min(hours_waiting / gap, 1.0))


def effort_weight(minutes: int) -> float:
    for limit, w in C.EFFORT:
        if minutes <= limit:
            return w
    return C.EFFORT_MAX


def score(counterparty: str, goal: str, loop: str, deadline: Optional[str], hours_waiting: float,
          effort_min: int, now: datetime, median_gap_h: Optional[float] = None) -> dict:
    s = C.STAKES.get(goal, C.STAKES["raise"]).get(counterparty, 0)
    l = C.LOOP.get(loop, 0)
    u = max(deadline_weight(deadline, now), lateness(hours_waiting, median_gap_h))
    e = effort_weight(effort_min)
    return {"S": s, "L": l, "U": round(u, 3), "E": e, "priority": round(s * l * u / e, 4)}


def soft_score(impact: float) -> dict:
    return {"impact": round(impact, 3), "mult": C.SOFT_SOURCE_MULT, "priority": round(impact * C.SOFT_SOURCE_MULT, 4)}


def market_impact(beta: float, magnitude: int, age_days: float, kind: str) -> float:
    return beta * magnitude * 0.5 ** (age_days / C.HALF_LIFE_DAYS.get(kind, 14))


def _key(i: Item):
    return (-i.priority, i.deadline or "9999", i.id)


def rank(items: List[Item], previous_top: List[str] = ()) -> List[Item]:
    """Open items above the floor, stable order, with hysteresis on slot #N."""
    pool = sorted([i for i in items if i.status == "open" and i.priority >= C.FLOOR], key=_key)
    top = pool[: C.TOP_N]
    if len(pool) > C.TOP_N and previous_top:
        last = top[-1]
        if last.id not in previous_top:
            incumbents = [i for i in pool[C.TOP_N:] if i.id in previous_top]
            if incumbents and last.priority < incumbents[0].priority * C.HYSTERESIS:
                top[-1] = incumbents[0]
                top.sort(key=_key)
    rest = [i for i in pool if i not in top]
    return top + rest
