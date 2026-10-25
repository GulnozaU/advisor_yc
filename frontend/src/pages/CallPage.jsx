import { useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { Mic, MicOff } from "lucide-react";
import { Operator } from "@/components/Operator";
import { PriorityCard } from "@/components/PriorityCard";
import { AdvisorBoard } from "@/components/AdvisorBoard";
import { DraftModal } from "@/components/DraftModal";
import { DemoPanel } from "@/components/DemoPanel";
import { useVoiceCall } from "@/hooks/useVoiceCall";
import { useCallTools } from "@/hooks/useCallTools";
import { usePriorities, isGuest } from "@/lib/api";
import { useAdvisor } from "@/lib/advisor";
import { clock } from "@/lib/format";

export default function CallPage() {
  const stage = useRef(null);
  const [params] = useSearchParams();
  const adv = useAdvisor();
  const advisorMode = adv.data && adv.data.mode !== "manual";
  const tools = useCallTools();
  const call = useVoiceCall(stage, { clientTools: advisorMode ? tools.clientTools : undefined });
  const { data: open = [] } = usePriorities("open");
  const live = call.state === "live";

  return (
    <div className="page call-page" data-testid="call-page">
      <section className="call-stage" ref={stage}>
        <div className="call-top">
          <span className={`live-pill ${live ? "on" : ""}`} data-testid="connection-indicator"><span className="dot" />{live ? "Live" : "Offline"}</span>
          <span className="timer" data-testid="call-timer">{clock(call.seconds)}</span>
        </div>
        <h1 className="display sm center">Speak with your advisor.</h1>
        <p className="muted center">A private voice line. Just ask naturally.</p>
        <Operator size={170} live={live} speaking={live && call.mode === "speaking"} mood={advisorMode ? tools.mood : "neutral"} />
        <p className={`call-status ${call.error ? "error" : ""}`} data-testid="call-status">{call.status}</p>
        <div className="call-controls">
          {live && (
            <button className={`btn-round ${call.muted ? "on" : ""}`} onClick={call.toggleMute} aria-label={call.muted ? "Unmute" : "Mute"} data-testid="mute-toggle-button">
              {call.muted ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
          )}
          <button className={`btn-primary call-btn ${live ? "end" : ""}`} disabled={call.state === "connecting"}
            onClick={live ? call.end : call.start} data-testid="call-toggle-button">
            {live ? "End call" : call.state === "connecting" ? "Connecting…" : "Start call"}
          </button>
        </div>
        {call.muted && <p className="muted small center" data-testid="muted-note">You're muted. The advisor can't hear you.</p>}
        {live && call.captions.length > 0 && (
          <div className="captions" data-testid="call-captions">
            {call.captions.slice(-2).map((c, i) => <p key={i}><b>{c.who}:</b> {c.text}</p>)}
          </div>
        )}
        {advisorMode && adv.data.mode === "demo" && (params.get("demo") === "1" || isGuest()) && <DemoPanel sendEvent={call.sendEvent} />}
      </section>
      <aside className="call-side" data-testid="call-priorities">
        <h2 className="section-title">On the table</h2>
        <p className="muted small">Your advisor sees these and opens with #1.</p>
        {advisorMode ? <div className="plist"><AdvisorBoard compact /></div> : (
        <div className="plist">
          {open.slice(0, 5).map((p, i) => <PriorityCard key={p.id} p={p} index={i} compact />)}
          {open.length === 0 && <div className="empty">No open priorities. The call will be a general check-in.</div>}
        </div>
        )}
      </aside>
      <DraftModal item={tools.drafting} mode={adv.data?.mode} onClose={() => tools.setDrafting(null)} onSent={() => { tools.setDrafting(null); adv.refetch(); }} />
    </div>
  );
}
