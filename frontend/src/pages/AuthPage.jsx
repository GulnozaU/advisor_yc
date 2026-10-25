import { SignIn, SignUp } from "@clerk/react";
import { Link } from "react-router-dom";
import { Operator } from "@/components/Operator";

export default function AuthPage({ mode }) {
  return (
    <div className="auth" data-testid={`${mode}-page`}>
      <aside className="auth-side">
        <Link to="/" className="brand"><b>Advisor</b> on Call</Link>
        <Operator size={200} testId="auth-operator" />
        <p className="auth-quote">"What's the one thing that moves the needle today?"</p>
      </aside>
      <div className="auth-main">
        <Link to="/" className="brand auth-brand-mobile"><b>Advisor</b> on Call</Link>
        {mode === "sign-in"
          ? <SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" withSignUp />
          : <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" />}
      </div>
    </div>
  );
}
