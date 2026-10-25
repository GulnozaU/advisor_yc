import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useApi, errorText } from "@/lib/api";

// Draft for one item: creates it on open (Claude writes it), sends only on an explicit click.
export const DraftModal = ({ item, mode, onClose, onSent }) => {
  const api = useApi();
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!item) return;
    setDraft(null); setError(null);
    api("post", `/advisor/items/${item.id}/draft`).then(setDraft).catch((e) => setError(errorText(e)));
  }, [item, api]);

  const send = async () => {
    setSending(true);
    try {
      const r = await api("post", `/advisor/drafts/${draft.id}/send`);
      toast(r.result === "simulated" ? "Demo: marked as sent (no real email went out)" : r.result === "already_sent" ? "Already sent" : "Sent from your Gmail");
      onSent(r.top);
    } catch (e) { toast.error(errorText(e)); } finally { setSending(false); }
  };

  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="aoc-dialog" data-testid="draft-modal">
        <DialogHeader><DialogTitle className="dialog-title">Draft reply</DialogTitle></DialogHeader>
        {!draft && !error && <div className="draft-loading" data-testid="draft-loading"><span className="loader" /> Writing the draft…</div>}
        {error && <p className="call-status error" data-testid="draft-error">{error}</p>}
        {draft && (
          <div className="draft" data-testid="draft-body">
            <p className="muted small">To <b>{draft.to}</b>{draft.cc?.length ? <> · Cc {draft.cc.join(", ")}</> : null}</p>
            <pre className="draft-text">{draft.body}</pre>
            {mode === "live" ? <p className="muted small">Saved in your Gmail Drafts. Send goes out from your Gmail to the people above only.</p>
              : <p className="muted small">Demo story: Send marks it done and nothing is really emailed.</p>}
            <button className="btn-primary" onClick={send} disabled={sending} data-testid="draft-send-button">{sending ? "Sending…" : "Send"}</button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
