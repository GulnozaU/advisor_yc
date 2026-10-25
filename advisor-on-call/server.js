import "dotenv/config";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import cors from "cors";
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const { ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID } = process.env;
const PORT = process.env.PORT || 3000;

function configProblem() {
  if (!ELEVENLABS_API_KEY) return "ELEVENLABS_API_KEY is missing in .env";
  if (!ELEVENLABS_API_KEY.startsWith("sk_") || ELEVENLABS_API_KEY.length !== 51)
    return "ELEVENLABS_API_KEY looks malformed (expected sk_… and 51 characters)";
  if (!ELEVENLABS_AGENT_ID) return "ELEVENLABS_AGENT_ID is missing in .env";
  if (!ELEVENLABS_AGENT_ID.startsWith("agent_")) return "ELEVENLABS_AGENT_ID should start with agent_";
  return null;
}

const client = ELEVENLABS_API_KEY ? new ElevenLabsClient({ apiKey: ELEVENLABS_API_KEY }) : null;
const app = express();
app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {
  const problem = configProblem();
  res.json({ status: "ok", configured: !problem, ...(problem && { problem }) });
});

app.get("/api/get-voice-token", async (_req, res) => {
  const problem = configProblem();
  if (problem) return res.status(500).json({ error: problem });
  try {
    const { signedUrl } = await client.conversationalAi.conversations.getSignedUrl({ agentId: ELEVENLABS_AGENT_ID });
    res.set("Cache-Control", "no-store").json({ signedUrl, token: signedUrl });
  } catch (err) {
    const status = err?.statusCode || 502;
    const hint =
      status === 401
        ? "API key rejected. It needs the ElevenAgents → Write permission."
        : status === 404
        ? "Agent not found. Check ELEVENLABS_AGENT_ID."
        : "Could not get a signed URL from ElevenLabs.";
    console.error("getSignedUrl failed:", status, err?.body || err?.message);
    res.status(status).json({ error: hint });
  }
});

app.use("/api", (_req, res) => res.status(404).json({ error: "Not found" }));
app.use(express.static(path.join(__dirname, "public")));
app.get("/{*splat}", (_req, res) => res.sendFile(path.join(__dirname, "public", "index.html")));

app.listen(PORT, "0.0.0.0", () => {
  console.log(`Advisor on Call running at http://localhost:${PORT}`);
  const problem = configProblem();
  if (problem) console.warn(`⚠ ${problem}`);
});
