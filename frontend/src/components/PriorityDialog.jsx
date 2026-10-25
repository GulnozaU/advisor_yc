import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { TYPES, toLocalInput } from "@/lib/format";

const EMPTY = { type: "send", action: "", who: "", reason: "", deadline: "" };

export const PriorityDialog = ({ open, onOpenChange, initial, onSave, busy }) => {
  const [f, setF] = useState(EMPTY);
  useEffect(() => { if (open) setF(initial ? { ...initial, deadline: toLocalInput(initial.deadline) } : EMPTY); }, [open, initial]);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = (e) => {
    e.preventDefault();
    if (!f.action.trim()) return;
    onSave({ type: f.type, action: f.action.trim(), who: f.who.trim(), reason: f.reason.trim(), deadline: f.deadline ? new Date(f.deadline).toISOString() : null });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="aoc-dialog" data-testid="priority-dialog">
        <DialogHeader><DialogTitle className="dialog-title">{initial ? "Edit priority" : "New priority"}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="profile-form">
          <div className="chips">
            {TYPES.map((t) => (
              <button type="button" key={t} className={`chip type-${t} ${f.type === t ? "on" : ""}`} onClick={() => setF({ ...f, type: t })} data-testid={`priority-type-${t}`}>{t}</button>
            ))}
          </div>
          <div className="field"><Label htmlFor="pr-action">Action</Label><Input id="pr-action" value={f.action} onChange={set("action")} placeholder="Reply to Sam about the pilot" data-testid="priority-action-input" /></div>
          <div className="grid2">
            <div className="field"><Label htmlFor="pr-who">Who it's for</Label><Input id="pr-who" value={f.who} onChange={set("who")} placeholder="Sam at Fernhill Finance" data-testid="priority-who-input" /></div>
            <div className="field"><Label htmlFor="pr-deadline">Deadline</Label><Input id="pr-deadline" type="datetime-local" value={f.deadline} onChange={set("deadline")} data-testid="priority-deadline-input" /></div>
          </div>
          <div className="field"><Label htmlFor="pr-reason">Why it matters</Label><Textarea id="pr-reason" rows={3} value={f.reason} onChange={set("reason")} placeholder="They asked twice and the pilot starts Monday." data-testid="priority-reason-input" /></div>
          <button className="btn-primary" disabled={!f.action.trim() || busy} data-testid="priority-save-button">{busy ? "Saving…" : "Save priority"}</button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
