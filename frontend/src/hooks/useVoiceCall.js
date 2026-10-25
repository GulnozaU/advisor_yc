import { useCallback, useEffect, useRef, useState } from "react";
import { Conversation } from "@elevenlabs/client";
import { useQueryClient } from "@tanstack/react-query";
import { useApi, errorText } from "@/lib/api";

// Live ElevenLabs call: status, mode, mute, timer, volume (written to --v on volumeEl) and call logging.
export function useVoiceCall(volumeEl) {
  const api = useApi();
  const qc = useQueryClient();
  const conv = useRef(null);
  const meta = useRef(null);
  const [state, setState] = useState("idle"); // idle | connecting | live
  const [mode, setMode] = useState("listening");
  const [status, setStatus] = useState("Ready when you are.");
  const [error, setError] = useState(false);
  const [muted, setMuted] = useState(false);
  const [seconds, setSeconds] = useState(0);

  const logCall = useCallback(async () => {
    const m = meta.current;
    meta.current = null;
    if (!m?.connectedAt) return;
    const duration_sec = Math.round((Date.now() - m.connectedAt) / 1000);
    try {
      await api("post", "/calls", { started_at: new Date(m.connectedAt).toISOString(), duration_sec, priority_ids: m.priorityIds });
      qc.invalidateQueries({ queryKey: ["calls"] });
    } catch {}
  }, [api, qc]);

  useEffect(() => {
    if (state !== "live") return;
    const t = setInterval(() => setSeconds(Math.round((Date.now() - meta.current?.connectedAt) / 1000) || 0), 500);
    let raf;
    const loop = () => {
      const v = mode === "speaking" && conv.current ? Math.min(1, conv.current.getOutputVolume() * 2.5) : 0;
      volumeEl.current?.style.setProperty("--v", v.toFixed(3));
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => { clearInterval(t); cancelAnimationFrame(raf); volumeEl.current?.style.setProperty("--v", 0); };
  }, [state, mode, volumeEl]);

  const start = useCallback(async () => {
    setError(false); setState("connecting"); setSeconds(0); setMuted(false);
    try {
      setStatus("Requesting microphone…");
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setStatus("Connecting…");
      const data = await api("get", "/voice-token");
      meta.current = { priorityIds: data.priorityIds };
      conv.current = await Conversation.startSession({
        signedUrl: data.signedUrl,
        connectionType: "websocket",
        dynamicVariables: data.dynamicVariables,
        onConnect: () => { meta.current.connectedAt = Date.now(); setState("live"); setStatus("Connected. Go ahead and speak."); },
        onDisconnect: () => { conv.current = null; setState("idle"); setMode("listening"); setStatus("Call ended."); logCall(); },
        onError: (msg) => { setError(true); setStatus(typeof msg === "string" ? msg : "Something went wrong."); },
        onModeChange: ({ mode: m }) => { setMode(m); setStatus(m === "speaking" ? "Advisor is speaking…" : "Listening…"); },
      });
    } catch (e) {
      conv.current = null; meta.current = null; setState("idle"); setError(true);
      setStatus(e?.name === "NotAllowedError" ? "Microphone access was denied." : errorText(e));
    }
  }, [api, logCall]);

  const end = useCallback(async () => { await conv.current?.endSession(); }, []);

  const toggleMute = useCallback(() => {
    setMuted((m) => { conv.current?.setMicMuted(!m); return !m; });
  }, []);

  useEffect(() => () => { conv.current?.endSession(); }, []);

  return { state, mode, status, error, muted, seconds, start, end, toggleMute };
}
