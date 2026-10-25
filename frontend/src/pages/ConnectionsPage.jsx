import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Mail, CalendarDays, Sparkles, PenLine, Search } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useApi, errorText } from "@/lib/api";
import { useAdvisor, useGoogleStatus, useCompetitors } from "@/lib/advisor";

const MODES = [
  { id: "manual", icon: PenLine, name: "Typed by me", body: "You keep the list by hand." },
  { id: "demo", icon: Sparkles, name: "Demo story", body: "Stripe Walker at Fernhill Finance: a full, fictional inbox and calendar. Nothing real is sent." },
  { id: "live", icon: Mail, name: "My Gmail & Calendar", body: "Ranks your real inbox and meetings. Drafts land in Gmail; Send only on your click." },
];

const GoogleRow = ({ id, icon: Icon, name, body, on }) => {
  const api = useApi();
  const connect = async () => {
    try { window.location.assign((await api("post", "/advisor/google/connect", { toolkit: id })).redirect_url); }
    catch (e) { toast.error(errorText(e)); }
  };
  return (
    <div className="conn" data-testid={`connection-${id}`}>
      <span className="conn-icon"><Icon size={20} /></span>
      <div><p className="conn-name">{name}</p><p className="muted small">{body}</p></div>
      {on ? <span className="conn-status on" data-testid={`connection-${id}-status`}>Connected</span>
        : <button className="btn-soft" onClick={connect} data-testid={`connect-${id}-button`}>Connect</button>}
    </div>
  );
};

const Competitors = () => {
  const api = useApi();
  const qc = useQueryClient();
  const { data = [] } = useCompetitors();
  const set = (d) => qc.setQueryData(["competitors"], d);
  const find = () => api("post", "/advisor/competitors/find").then(set).catch((e) => toast.error(errorText(e)));
  const toggle = (c) => api("post", "/advisor/competitors/confirm", { domain: c.domain, confirmed: !c.confirmed }).then(set).catch((e) => toast.error(errorText(e)));
  return (
    <section className="panel" data-testid="competitors-panel">
      <div className="board-head">
        <div><h2 className="section-title">Competitors</h2><p className="muted small">Confirm the real ones. Their pricing and homepage are checked on every sync.</p></div>
        <button className="btn-soft" onClick={find} data-testid="find-competitors-button"><Search size={15} /> Find</button>
      </div>
      {data.length === 0 ? <div className="empty">Uses your website and one-liner from Settings.</div> : (
        <div className="chips">
          {data.map((c) => (
            <button key={c.domain} className={`chip ${c.confirmed ? "on" : ""}`} onClick={() => toggle(c)} title={c.reason || c.title || c.domain} data-testid={`competitor-${c.domain}`}>
              {c.name}{c.confirmed && c.beta ? ` · ${c.beta >= 0.6 ? "high" : c.beta >= 0.3 ? "medium" : "low"} overlap` : ""}
            </button>
          ))}
        </div>
      )}
    </section>
  );
};

export default function ConnectionsPage() {
  const api = useApi();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const { data } = useAdvisor();
  const mode = data?.mode;
  const google = useGoogleStatus(mode === "live");
  useEffect(() => {
    if (!params.get("connected")) return;
    toast("Google connected. Pulling in your inbox…");
    google.refetch();
    api("post", "/advisor/sync").then(() => { qc.invalidateQueries({ queryKey: ["advisor"] }); toast("Your top 5 is ready on the dashboard"); })
      .catch((e) => toast.error(errorText(e)));
  }, [params]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = async (m) => {
    try {
      const r = await api("post", "/advisor/mode", { mode: m });
      qc.setQueryData(["advisor"], (d) => ({ ...d, mode: m, top: r.items }));
      qc.invalidateQueries({ queryKey: ["advisor"] });
      toast(m === "demo" ? "Demo story loaded" : m === "live" ? "Using your Gmail & Calendar" : "Back to your typed list");
    } catch (e) { toast.error(errorText(e)); }
  };

  return (
    <div className="page narrow" data-testid="connections-page">
      <header className="page-head rise">
        <p className="eyebrow">Connections</p>
        <h1 className="display sm">Where your list comes from</h1>
      </header>
      <div className="mode-grid rise d1">
        {MODES.map(({ id, icon: Icon, name, body }) => (
          <button key={id} className={`mode-card ${mode === id ? "on" : ""}`} onClick={() => pick(id)} data-testid={`mode-${id}`}>
            <Icon size={18} /><p className="conn-name">{name}</p><p className="muted small">{body}</p>
          </button>
        ))}
      </div>
      {mode === "live" && (
        <div className="conn-list rise d2">
          <GoogleRow id="gmail" icon={Mail} name="Gmail" body="Reads the last 30 days to find replies you owe." on={google.data?.gmail} />
          <GoogleRow id="googlecalendar" icon={CalendarDays} name="Google Calendar" body="Last 7 days and next 14 days of meetings." on={google.data?.googlecalendar} />
          {google.isError && <p className="call-status error">{errorText(google.error)}</p>}
        </div>
      )}
      {mode === "live" && <div className="rise d3" style={{ marginTop: 20 }}><Competitors /></div>}
    </div>
  );
}
