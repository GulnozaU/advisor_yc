# DIAGNOSTIC — Founder Advisor backend (Emergent build)

This was built inside the existing React + FastAPI + MongoDB app, not the Next.js + Supabase stack from the original prompt. The user chose this: a real backend in this preview, with MongoDB standing in for Supabase.

## What was built against the spec
| Spec | Status | Notes |
|---|---|---|
| Item schema, validation at boundaries | PASS | Pydantic models in `backend/advisor/types.py` (zod equivalent) |
| Prefilter / scorer / ranker as pure functions | PASS | `advisor/pipeline.py`, `advisor/scoring.py`; constants in `scoring_constants.py` |
| Fixtures relative to now, golden ranking | PASS | 25 threads, 10 events; `tests/test_advisor_pipeline.py` 15/15 |
| DEMO_MODE end to end without Google | PASS | "Demo story" source, plus a guest "Try it now" with no sign-up |
| Composio Gmail/Calendar live path | UNVERIFIED | Code in `advisor/google.py`; no COMPOSIO_API_KEY was provided |
| Claude labeler (haiku-4-5), drafts (sonnet-4-5) | UNVERIFIED | No ANTHROPIC_API_KEY. Demo drafts use a labelled template; demo labels are gold fixture labels |
| Exa competitors, diffs, crisis tone | UNVERIFIED | Code in `advisor/market.py`; no EXA_API_KEY |
| Playbook atoms with sources | PASS (3 atoms) | `data/playbook.json`; fires only on triggers |
| ElevenLabs agent config via API | PASS | 5 client tools registered; first_message `{{opening_line}}`; prompt uses brief/founder_name/goal/tone_note |
| Live [EVENT] injection | PASS | Testing agent: the agent spoke the price-cut event mid-call (sendUserMessage) |
| Send only on click, once | PASS | Unique (uid, draft_id); a second send returns `already_sent` |
| RAG memories + lookup | PASS | Mongo text index (stands in for Postgres FTS/GIN); 5 facts, under 2000 chars, source-tagged, untrusted-wrapped; measured ~2 ms; per-user isolation tested |
| Advisor Google Calendar auto-add | NOT BUILT | Cut first, per the spec's cut order |
| Founder inference from sent mail | NOT BUILT | Onboarding form is used instead |

## Constant adjustments (1)
- `STAKES["raise"]["customer"] = 5` (the example table implied 4). This is needed so Beta Corp ranks above Priya, as `expected` requires.

## Measured
- Lookup p50 about 2 ms on preview, for both a hit and a miss (call_log `rag.lookup`).
- Golden ranking scores: Beta 3.46, Priya 2.94, Acme 1.0, Tom 0.58, playbook 0.5. The price-cut market item lands at #3 (2.0). The new investor email lands at #3 (2.69).

## Testing
- iteration_3: dashboard. iteration_4: advisor, guest and voice. Backend 15 + 19 + 19 tests passing.
- Fixed after iteration_4: upstream failures now return 424 with the app's message instead of the Cloudflare 502 page; a stale guest flag now redirects to the landing page; score labels are rounded.

## Manual checks left for you
- Add the Anthropic, Composio and Exa keys. Then connect Gmail and Calendar, check that a draft appears in Gmail Drafts, and send the first real email to your own address.
- A microphone test on a real device.

## Open risks
- The Composio response shapes are parsed defensively but were not tested against a real account (about 40% chance they need tweaks).
- Guests can use agent minutes; there is no rate limit yet.
