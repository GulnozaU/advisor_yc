import { useEffect, useState } from "react";
import { AnimatePresence, Reorder, motion, useDragControls } from "framer-motion";
import { Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { usePriorities, useApiMutation, useApi, errorText } from "@/lib/api";
import { PriorityCard } from "@/components/PriorityCard";
import { PriorityDialog } from "@/components/PriorityDialog";

const DraggableCard = ({ p, index, actions, onDragEnd }) => {
  const controls = useDragControls();
  return (
    <Reorder.Item value={p} dragListener={false} dragControls={controls} onDragEnd={onDragEnd} className="reorder-item"
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 40 }} transition={{ duration: 0.25 }}>
      <PriorityCard p={p} index={index} dragControls={controls} {...actions(p)} />
    </Reorder.Item>
  );
};

export const PriorityBoard = () => {
  const api = useApi();
  const open = usePriorities("open");
  const closed = usePriorities("closed");
  const [items, setItems] = useState([]);
  const [dialog, setDialog] = useState({ open: false, item: null });
  const [researching, setResearching] = useState(false);
  const qc = useQueryClient();
  const research = async () => {
    setResearching(true);
    try { qc.setQueryData(["priorities", "open"], await api("post", "/priorities/suggest")); toast("Fresh priorities from research on your startup"); }
    catch (e) { toast.error(errorText(e)); } finally { setResearching(false); }
  };
  useEffect(() => { if (open.data) setItems(open.data); }, [open.data]);

  const inv = ["priorities"];
  const create = useApiMutation("post", "/priorities", inv);
  const patch = useApiMutation("patch", (v) => `/priorities/${v.id}`, inv);
  const remove = useApiMutation("delete", (v) => `/priorities/${v.id}`, inv);
  const run = (m, vars, msg) => m.mutateAsync(vars).then(() => msg && toast(msg)).catch((e) => toast.error(errorText(e)));

  const save = async (body) => {
    await run(dialog.item ? patch : create, dialog.item ? { id: dialog.item.id, body } : body, dialog.item ? "Priority updated" : "Priority added");
    setDialog({ open: false, item: null });
  };
  const persistOrder = () => api("post", "/priorities/reorder", { ids: items.map((p) => p.id) }).catch((e) => toast.error(errorText(e)));
  const actions = (p) => ({
    onEdit: () => setDialog({ open: true, item: p }),
    onDone: () => run(patch, { id: p.id, body: { status: "done" } }, "Nice. Marked done."),
    onDismiss: () => run(patch, { id: p.id, body: { status: "dismissed" } }, "Dismissed"),
    onReopen: () => run(patch, { id: p.id, body: { status: "open" } }, "Back on the list"),
    onDelete: () => run(remove, { id: p.id }, "Deleted"),
  });

  return (
    <section className="board" data-testid="priority-board">
      <div className="board-head">
        <div>
          <h2 className="section-title">Top 5 priorities</h2>
          <p className="muted">Drag to reorder. Your advisor opens the call with #1.</p>
        </div>
        <div className="board-actions">
          <button className="btn-soft" onClick={research} disabled={researching} data-testid="suggest-priorities-button">
            <Sparkles size={15} /> {researching ? "Researching…" : "Research my startup"}
          </button>
          <button className="btn-soft" onClick={() => setDialog({ open: true, item: null })} data-testid="add-priority-button"><Plus size={16} /> Add</button>
        </div>
      </div>
      <Tabs defaultValue="open">
        <TabsList className="aoc-tabs">
          <TabsTrigger value="open" data-testid="tab-open">Open ({items.length})</TabsTrigger>
          <TabsTrigger value="done" data-testid="tab-done">Done ({closed.data?.length ?? 0})</TabsTrigger>
        </TabsList>
        <TabsContent value="open">
          {open.isLoading ? <div className="skeleton-card" /> : items.length === 0 ? (
            <div className="empty" data-testid="priorities-empty">Nothing on your list. Add what matters most this week.</div>
          ) : (
            <Reorder.Group axis="y" values={items} onReorder={setItems} className="plist">
              <AnimatePresence initial={false}>
                {items.map((p, i) => (
                  <DraggableCard key={p.id} p={p} index={i} actions={actions} onDragEnd={persistOrder} />
                ))}
              </AnimatePresence>
            </Reorder.Group>
          )}
        </TabsContent>
        <TabsContent value="done">
          <div className="plist">
            {(closed.data || []).length === 0 && <div className="empty">Completed and dismissed items land here.</div>}
            {(closed.data || []).map((p) => (
              <motion.div key={p.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }}><PriorityCard p={p} {...actions(p)} /></motion.div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
      <PriorityDialog open={dialog.open} initial={dialog.item} busy={create.isPending || patch.isPending}
        onOpenChange={(o) => setDialog((d) => ({ ...d, open: o }))} onSave={save} />
    </section>
  );
};
