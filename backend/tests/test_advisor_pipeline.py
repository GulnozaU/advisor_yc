import pytest
from datetime import datetime, timedelta, timezone

from advisor import fixtures, pipeline, scoring
from advisor.types import Event, Item, Label, Thread

NOW = datetime.now(timezone.utc)


def run_fixtures(now=NOW, market=()):
    data = fixtures.build(now)
    threads = [Thread(**t) for t in data["threads"]]
    events = [Event(**e) for e in data["events"]]
    labels = {t.id: t.label for t in threads if t.label}
    contacts = {"ceo@betacorp.example.com": "Sam at Beta Corp", "priya@fundx.example.com": "Priya at Fund X",
                "dana@acme.example.com": "Dana at Acme", "tom@advisors.example.com": "Tom, your advisor"}
    items = pipeline.build_items("u1", data["founder"], threads, events, labels, now, contacts, list(market), {})
    return scoring.rank(items)


def test_golden_ranking():
    ranked = run_fixtures()
    assert [i.ref_key for i in ranked[:5]] == fixtures.EXPECTED["order"]
    assert ranked[0].action.startswith("Reply to Sam at Beta Corp before your Beta Corp renewal in 3 hours")


def test_excluded_never_ranked():
    keys = {i.ref_key for i in run_fixtures()}
    assert not keys & set(fixtures.EXPECTED["excluded"])


def test_deterministic():
    assert [i.ref_key for i in run_fixtures()] == [i.ref_key for i in run_fixtures()]


@pytest.mark.parametrize("hours,expected", [(-1, 1.0), (5, 0.9), (23, 0.7), (71, 0.4), (100, 0.1)])
def test_deadline_buckets(hours, expected):
    assert scoring.deadline_weight((NOW + timedelta(hours=hours)).isoformat(), NOW) == expected


def test_lateness_monotonic():
    vals = [scoring.lateness(h, None) for h in range(0, 100, 5)]
    assert vals == sorted(vals) and vals[-1] == 1.0


def test_effort():
    assert [scoring.effort_weight(m) for m in (5, 15, 30, 60)] == [1.0, 1.3, 1.7, 1.7]


def _it(i, p):
    return Item(id=i, uid="u", ref_key=i, kind="send", action=i, source="thread", priority=p, created_at="x", updated_at="x")


def test_hysteresis_and_floor():
    old = [_it(f"o{i}", 1.0 - i * 0.1) for i in range(5)]  # o4 = 0.6
    challenger = _it("new", 0.65)  # < 0.6 * 1.2, cannot displace
    ranked = scoring.rank(old + [challenger], previous_top=[o.id for o in old])
    assert "new" not in [i.id for i in ranked[:5]]
    strong = _it("strong", 0.8)
    assert "strong" in [i.id for i in scoring.rank(old + [strong], previous_top=[o.id for o in old])[:5]]
    assert "tiny" not in [i.id for i in scoring.rank([_it("tiny", 0.01)])]


def test_tie_order_stable():
    a, b = _it("a", 1.0), _it("b", 1.0)
    assert [i.id for i in scoring.rank([b, a])] == ["a", "b"]


def test_soft_multiplier_and_market_rank():
    market = [{"id": "m1", "name": "Rivalyst", "fact": "Rivalyst cut its tier 2 price by 30%.", "beta": 1.0, "magnitude": 4,
               "kind": "pricing", "created_at": NOW.isoformat()}]
    ranked = run_fixtures(market=market)
    keys = [i.ref_key for i in ranked]
    assert keys.index("market:m1") == 2
    assert "Rivalyst" in ranked[0].why  # joined into the Beta thread


def test_injection_thread_has_no_item():
    assert all("inject" not in i.ref_key for i in run_fixtures())


def test_evidence_is_substring():
    data = fixtures.build(NOW)
    for t in data["threads"]:
        if t["label"]:
            text = pipeline.thread_text(Thread(**t))
            assert t["label"]["evidence"] in text, t["id"]
