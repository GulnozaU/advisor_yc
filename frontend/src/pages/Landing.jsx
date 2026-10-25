import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Operator } from "@/components/Operator";
import { startGuest, errorText } from "@/lib/api";

export const TryAuto = () => {
  const nav = useNavigate();
  const [err, setErr] = useState(null);
  useEffect(() => { startGuest().then(() => nav("/dashboard", { replace: true })).catch((e) => setErr(errorText(e))); }, [nav]);
  return <div className="page-loading" data-testid="try-loading">{err || <span className="loader" />}</div>;
};

export const TryButton = ({ className = "btn-primary", label = "Try it now, no sign-up" }) => {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    try { await startGuest(); nav("/dashboard"); } catch (e) { toast.error(errorText(e)); setBusy(false); }
  };
  return <button className={className} onClick={go} disabled={busy} data-testid="landing-try-button">{busy ? "Loading the demo…" : label}</button>;
};

export default function Landing() {
  return (
    <div className="landing" data-testid="landing-page">
      <header className="landing-top">
        <div className="brand"><b>Advisor</b> on Call</div>
        <Link to="/sign-in" className="link" data-testid="landing-login-link">Log in</Link>
      </header>
      <main className="landing-main">
        <div className="landing-copy rise">
          <p className="eyebrow">For early-stage founders</p>
          <h1 className="display">Your top five things,<br />talked through out loud.</h1>
          <p className="lede">Keep a short list of what matters this week. Then call your advisor. It already knows your list and opens with the one thing you should do first, and why.</p>
          <div className="cta-row">
            <TryButton />
            <Link to="/sign-up" className="btn-ghost" data-testid="landing-signup-button">Sign up free</Link>
            <Link to="/sign-in" className="btn-ghost" data-testid="landing-signin-button">Log in</Link>
          </div>
        </div>
        <div className="landing-art rise d2"><Operator size={240} testId="landing-operator" /></div>
      </main>
      <footer className="landing-foot">A private voice line. Just ask naturally.</footer>
    </div>
  );
}
