export const GOALS = [
  { value: "raise", label: "Raise" },
  { value: "first_customers", label: "First customers" },
  { value: "revenue", label: "Revenue" },
  { value: "ship", label: "Ship" },
  { value: "hire", label: "Hire" },
];

export const TYPES = ["send", "meet", "decide", "learn"];

export function countdown(deadline) {
  if (!deadline) return { text: "No deadline", tone: "calm" };
  const ms = new Date(deadline) - Date.now();
  if (ms < 0) return { text: "Overdue", tone: "late" };
  const h = Math.floor(ms / 3.6e6);
  if (h < 24) return { text: h < 1 ? "Due within the hour" : `${h}h left`, tone: "soon" };
  const d = Math.round(h / 24);
  return { text: `${d} day${d === 1 ? "" : "s"} left`, tone: d <= 2 ? "soon" : "calm" };
}

export const clock = (sec) => `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

export const shortDate = (iso) =>
  new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export const toLocalInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
