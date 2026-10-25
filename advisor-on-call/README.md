# Advisor on Call

Single-page voice call screen powered by an ElevenLabs agent.

```bash
cp .env.example .env   # fill in ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID
npm install
npm start              # http://localhost:3000
```

- API key must have **ElevenAgents → Write** permission (TTS/STT/Speech-to-Speech scopes are not enough).
- `GET /api/get-voice-token` → `{ signedUrl, token }` (key never leaves the server)
- `GET /api/health` → `{ status, configured }`
- Speak while the advisor talks to interrupt it.
