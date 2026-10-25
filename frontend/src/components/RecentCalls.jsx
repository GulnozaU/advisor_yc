import { Link } from "react-router-dom";
import { PhoneCall } from "lucide-react";
import { useCalls } from "@/lib/api";
import { clock, shortDate } from "@/lib/format";

export const CallRow = ({ c }) => (
  <div className="call-row" data-testid={`call-row-${c.id}`}>
    <span className="call-icon"><PhoneCall size={15} /></span>
    <div className="call-info">
      <p className="call-date">{shortDate(c.started_at)}</p>
      <p className="muted small">{c.priorities.length ? c.priorities.map((p) => p.action).join(" · ") : "No open priorities at the time"}</p>
    </div>
    <span className="call-len" data-testid={`call-duration-${c.id}`}>{clock(c.duration_sec)}</span>
  </div>
);

export const RecentCalls = ({ limit = 3 }) => {
  const { data = [], isLoading } = useCalls();
  return (
    <section className="recent" data-testid="recent-calls">
      <div className="board-head">
        <h2 className="section-title">Recent calls</h2>
        {data.length > limit && <Link to="/calls" className="link" data-testid="see-all-calls-link">See all</Link>}
      </div>
      {isLoading ? <div className="skeleton-card" /> : data.length === 0 ? (
        <div className="empty" data-testid="calls-empty">No calls yet. Your first one takes about five minutes.</div>
      ) : data.slice(0, limit).map((c) => <CallRow key={c.id} c={c} />)}
    </section>
  );
};
