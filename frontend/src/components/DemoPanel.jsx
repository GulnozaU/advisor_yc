import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useApi, errorText } from "@/lib/api";

// Hidden demo harness (?demo=1): inject a live market event or a new investor email.
export const DemoPanel = ({ sendEvent }) => {
  const api = useApi();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(null);
  const fire = async (kind) => {
    setBusy(kind);
    try {
      const r = await api("post", "/advisor/demo/event", { kind });
      qc.setQueryData(["advisor"], (d) => ({ ...d, top: r.top }));
      const spoken = sendEvent(r.event);
      toast(spoken ? "Event sent to the advisor" : "Added to the list. Start a call to hear it live.");
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(null); }
  };
  return (
    <div className="demo-panel" data-testid="demo-panel">
      <p className="eyebrow">Demo panel</p>
      <button className="btn-soft" disabled={!!busy} onClick={() => fire("price_cut")} data-testid="demo-price-cut-button">Competitor price cut</button>
      <button className="btn-soft" disabled={!!busy} onClick={() => fire("investor_email")} data-testid="demo-investor-email-button">New investor email</button>
    </div>
  );
};
