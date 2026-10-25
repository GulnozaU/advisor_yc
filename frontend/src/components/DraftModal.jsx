import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useApi, errorText } from "@/lib/api";

const PLACEHOLDER = /\[[^[\]\n]{1,60}\]/g;

// Draft for one item: creates it on open (Claude writes it), sends only on an explicit click once every [placeholder] is filled.
export const DraftModal = ({ item, mode, onClose, onSent }) => {
  const api = useApi();
  const box = useRef(null);
  const [draft, setDraft] = useState(null);
  const [text, setText] = useState("");
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!item) return;
    setDraft(null); setError(null);
    api("post", `/advisor/items/${item.id}/draft`).then((d) => { setDraft(d); setText(d.body); }).catch((e) => setError(errorText(e)));
  }, [item, api]);

  const holes = [...text.matchAll(PLACEHOLDER)];
  const jump = (m) => { box.current?.focus(); box.current?.setSelectionRange(m.index, m.index + m[0].length); };

  const send = async () => {
    setSending(true);
    try {
      const r = await api("post", `/advisor/drafts/${draft.id}/send`, { body: text });
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
            <textarea ref={box} className="draft-text" rows={9} value={text} onChange={(e) => setText(e.target.value)} data-testid="draft-textarea" />
            {holes.length > 0 && (
              <div className="fill-ins" data-testid="draft-fillins">
                <span>Fill in before sending:</span>
                {holes.map((m, i) => (
                  <button key={`${m.index}-${i}`} className="fill-chip" onClick={() => jump(m)} data-testid={`draft-fillin-${i}`}>{m[0]}</button>
                ))}
              </div>
            )}
            {mode === "live" ? <p className="muted small">Saved in your Gmail Drafts. Send goes out from your Gmail to the people above only.</p>
              : <p className="muted small">Demo story: Send marks it done and nothing is really emailed.</p>}
            <button className="btn-primary" onClick={send} disabled={sending || holes.length > 0} data-testid="draft-send-button">
              {sending ? "Sending…" : holes.length ? `Fill ${holes.length} blank${holes.length > 1 ? "s" : ""} to send` : "Send"}
            </button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
