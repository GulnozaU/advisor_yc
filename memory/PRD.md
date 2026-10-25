# Advisor on Call — PRD

## Original problem
Express + static HTML voice call screen. GET /api/get-voice-token (ElevenLabs getSignedUrl → {signedUrl, token}), GET /api/health, .env (ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, PORT=3000). index.html: Start/End call, status; mic → token → Conversation.startSession({signedUrl, connectionType:"websocket"}). Runnable with npm install && npm start.

## User choices
Standalone Express app + live preview here; keys entered via the secure form; clean, minimal, calm premium look.

## Architecture
- /app/advisor-on-call: server.js (Express 5, @elevenlabs/elevenlabs-js), public/index.html (@elevenlabs/client via esm.sh), .env.example, README
- Preview: frontend supervisor runs Express on :3000 (frontend/package.json start script, reads /app/backend/.env); backend/server.py is a preview-only proxy that sends /api/* to Express

## Implemented (June 2026)
- Signed URL endpoint with key/agent format checks and clear error hints (401 → needs ElevenAgents Write)
- Health endpoint, JSON 404 for unknown /api paths
- Call screen: orb animation, live/offline indicator, speaking/listening status, mic-denied handling
- Tested end to end, live ElevenLabs session connects and ends cleanly

## Backlog
- P1: Live transcript of the call
- P1: Rate limiting on token endpoint
- P2: Mute button, call timer
