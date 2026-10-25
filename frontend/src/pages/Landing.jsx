import { Link } from "react-router-dom";
import { Operator } from "@/components/Operator";

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
            <Link to="/sign-up" className="btn-primary" data-testid="landing-signup-button">Sign up free</Link>
            <Link to="/sign-in" className="btn-ghost" data-testid="landing-signin-button">Log in</Link>
          </div>
        </div>
        <div className="landing-art rise d2"><Operator size={240} testId="landing-operator" /></div>
      </main>
      <footer className="landing-foot">A private voice line. Just ask naturally.</footer>
    </div>
  );
}
