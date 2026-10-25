# Advisor on Call — PRD

## Original problem
Started as an Express + static HTML ElevenLabs voice call screen (kept in /app/advisor-on-call). Approved plan (Oct 2026): a signed-in founder dashboard. Founders sign up, set up a profile, manage their top-5 priorities and call the orange advisor, which already knows those priorities. The team's Gmail, Calendar, ranking and competitor pipeline plugs in later.

## Architecture
- React (CRA/craco) frontend + FastAPI + MongoDB backend
- Auth: Emergent-managed Clerk (email+password and Google), with `require_user` on every data route
- Voice: ElevenLabs signed URL from `/api/voice-token`. The browser `@elevenlabs/client` sends dynamicVariables (founder_name, company, one_liner, goal, top_priority, top_priority_reason, priorities)
- Character: `@rive-app/canvas` with `/orange-operator.riv` and a CSS talking-mouth overlay driven by output volume
- Collections: profiles, priorities (rank, status open/done/dismissed, sample), calls (duration, priority snapshot)
- Agent prompt and first message for ElevenLabs: /app/docs/elevenlabs-agent-setup.md

## Implemented
- 2026-10: Standalone Express call screen, orange palette, Rive character, lip sync
- 2026-10: Founder dashboard MVP:
  - landing page, sign-in and sign-up, onboarding
  - dashboard with the top-5 board (add, edit, drag reorder, done, dismiss, delete, Done tab, 3 sample items)
  - call page with mute and timer, call logging, Calls page
  - honest Connections page, Settings
  - mobile bottom bar
- Tested: iteration_3. Backend 19/19 passing, full UI flow passing, mobile overflow fixed
- 2026-10: Founder Advisor backend (`backend/advisor/`):
  - S×L×U/E scorer and ranker with hysteresis, floor and 0.5 soft multiplier; demo fixtures and golden tests
  - Composio Gmail/Calendar, Claude labeler and drafts, Exa competitors and crisis tone: UNVERIFIED, no keys
  - playbook atoms, live [EVENT] demo panel, 5 ElevenLabs client tools configured via API
  - RAG `memories` with Mongo text index and lookup; guest "Try it now" (cookie, demo only)
  - See /app/DIAGNOSTIC.md. Tested in iterations 4-6
- GitHub: merged into main in a local clone at /root/advisor_yc (21 commits ahead). Push blocked: the GITHUB_TOKEN is read-only (403)

## Backlog
- P0 (Phase 2): team pipeline feeds real priorities and drafts; draft cards with one-click Send; re-ranking when the founder pushes back on a call; competitor interruptions
- P1: shadcn date picker for deadlines; bulk reorder write; call transcript summary
- P2 (Phase 3): waitlist, paid plan, Zoom bot via Recall
