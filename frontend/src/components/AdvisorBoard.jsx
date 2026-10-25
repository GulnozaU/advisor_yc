import { useState } from "react";
import { AnimatePresence } from "framer-motion";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useApi, errorText } from "@/lib/api";
import { useAdvisor } from "@/lib/advisor";
import { AdvisorCard } from "@/components/AdvisorCard";
import { DraftModal } from "@/components/DraftModal";

const MODE_LABEL = { demo: "Demo story", live: "Your Gmail & Calendar" };

export const AdvisorBoard = ({ compact = false }) => {
  const api = useApi();
  const qc = useQueryClient();
  const { data, isLoading } = useAdvisor();
  const [syncing, setSyncing] = useState(false);
  const [drafting, setDrafting] = useState(null);
  const top = data?.top || [];
  const put = (t) => qc.setQueryData(["advisor"], (d) => ({ ...d, top: t }));
  const act = (it, status, msg) => api("post", `/advisor/items/${it.id}/status`, { status }).then((r) => { put(r.top); toast(msg); qc.invalidateQueries({ queryKey: ["advisor"] }); }).catch((e) => toast.error(errorText(e)));
  const refresh = async () => {
    setSyncing(true);
    try { put((await api("post", "/advisor/sync")).top); toast("Up to date"); } catch (e) { toast.error(errorText(e)); } finally { setSyncing(false); }
  };

  return (
    <section className={compact ? "" : "board"} data-testid="advisor-board">
      {!compact && (
        <div className="board-head">
          <div>
            <h2 className="section-title">Top 5 right now</h2>
            <p className="muted">Ranked from {MODE_LABEL[data?.mode] || "your sources"}. Your advisor opens with #1.</p>
          </div>
          <button className="btn-soft" onClick={refresh} disabled={syncing} data-testid="advisor-refresh-button">
            <RefreshCw size={15} className={syncing ? "spin" : ""} /> {syncing ? "Syncing" : "Refresh"}
          </button>
        </div>
      )}
      {isLoading ? <div className="skeleton-card" /> : top.length === 0 ? (
        <div className="empty" data-testid="advisor-empty">You're clear. Nothing needs you right now, so pick one deep-work move.</div>
      ) : (
        <div className="plist">
          <AnimatePresence mode="popLayout" initial={false}>
            {top.map((it, i) => (
              <AdvisorCard key={it.id} it={it} index={i} compact={compact} onSend={setDrafting}
                onDone={(x) => act(x, "done", "Nice. Marked done.")} onDismiss={(x) => act(x, "dismissed", "Dismissed")} />
            ))}
          </AnimatePresence>
        </div>
      )}
      <DraftModal item={drafting} mode={data?.mode} onClose={() => setDrafting(null)} onSent={(t) => { put(t); setDrafting(null); }} />
    </section>
  );
};
