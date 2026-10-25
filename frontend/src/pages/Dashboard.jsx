import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Operator } from "@/components/Operator";
import { PriorityBoard } from "@/components/PriorityBoard";
import { AdvisorBoard } from "@/components/AdvisorBoard";
import { RecentCalls } from "@/components/RecentCalls";
import { useMe, usePriorities } from "@/lib/api";
import { useAdvisor } from "@/lib/advisor";

const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
};

export default function Dashboard() {
  const { data: me } = useMe();
  const { data: manual = [] } = usePriorities("open");
  const { data: adv } = useAdvisor();
  const advisorMode = adv && adv.mode !== "manual";
  const open = advisorMode ? adv.top : manual;
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  return (
    <div className="page" data-testid="dashboard-page">
      <header className="page-head rise">
        <p className="eyebrow" data-testid="dashboard-date">{today}</p>
        <h1 className="display sm" data-testid="dashboard-greeting">{greeting()}, {adv?.mode === "demo" ? "Carl" : me?.name?.split(" ")[0]}.</h1>
        {adv?.mode === "demo" && <p className="muted small" data-testid="demo-note">Demo story: you're Carl Walker, founder of Fernhill Finance. Nothing real is sent.</p>}
      </header>
      <div className="dash-grid">
        <Link to="/call" className="call-tile rise d1" data-testid="start-call-tile">
          <Operator size={150} testId="dashboard-operator" />
          <div className="call-tile-copy">
            <p className="eyebrow light">Your advisor is in</p>
            <p className="call-tile-title">Start call</p>
            <p className="call-tile-sub">{open[0] ? <>Opens with: <b>{open[0].action}</b></> : "Add a priority so your advisor has something to open with."}</p>
            <span className="call-tile-go">Call now <ArrowRight size={16} /></span>
          </div>
        </Link>
        <div className="rise d2">{advisorMode ? <AdvisorBoard /> : <PriorityBoard />}</div>
        <div className="rise d3 recent-col"><RecentCalls /></div>
      </div>
    </div>
  );
}
