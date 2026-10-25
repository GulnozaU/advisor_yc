import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useApi, errorText } from "@/lib/api";

// Client tools for the ElevenLabs agent. Names and parameters match advisor/agent_setup.py.
export function useCallTools() {
  const api = useApi();
  const qc = useQueryClient();
  const [mood, setMood] = useState("neutral");
  const [drafting, setDrafting] = useState(null);

  const clientTools = useMemo(() => {
    const top3 = (top) => top.slice(0, 3).map((t, i) => `#${i + 1} ${t.action} (id ${t.id})`).join("; ");
    const refresh = (top) => qc.setQueryData(["advisor"], (d) => ({ ...d, top }));
    const safe = (fn) => async (p) => { try { return await fn(p || {}); } catch (e) { return `Tool failed: ${errorText(e)}`; } };
    return {
      lookup: safe(async ({ query }) => (await api("post", "/advisor/lookup", { query })).result),
      draft_email: safe(async ({ item_id }) => {
        const d = await api("post", `/advisor/items/${item_id}/draft`);
        setDrafting({ id: item_id });
        return `Draft to ${d.to} is open on screen for the founder to review and send. First line: ${d.body.split("\n")[0]}`;
      }),
      complete_item: safe(async ({ item_id }) => {
        const r = await api("post", `/advisor/items/${item_id}/status`, { status: "done" });
        refresh(r.top);
        return `Marked done. New top 3: ${top3(r.top)}`;
      }),
      reprioritize: safe(async ({ item_id, reason }) => {
        const r = await api("post", `/advisor/items/${item_id}/reprioritize`, { reason });
        refresh(r.top);
        return `Re-ranked. New top 3: ${top3(r.top)}`;
      }),
      set_mood: ({ mood: m }) => { if (["neutral", "pleased", "concerned", "urgent"].includes(m)) setMood(m); return "ok"; },
    };
  }, [api, qc]);

  return { clientTools, mood, drafting, setDrafting };
}
