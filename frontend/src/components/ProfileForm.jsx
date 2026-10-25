import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GOALS } from "@/lib/format";

const Field = ({ id, label, children }) => (
  <div className="field">
    <Label htmlFor={id}>{label}</Label>
    {children}
  </div>
);

export const ProfileForm = ({ initial = {}, submitLabel, onSubmit, busy }) => {
  const [f, setF] = useState({ name: "", company: "", one_liner: "", website: "", goal: "", ...initial });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const valid = f.name.trim() && f.company.trim() && f.goal;
  const submit = (e) => { e.preventDefault(); if (valid) onSubmit({ name: f.name.trim(), company: f.company.trim(), one_liner: f.one_liner.trim(), website: f.website.trim(), goal: f.goal }); };

  return (
    <form onSubmit={submit} className="profile-form" data-testid="profile-form">
      <div className="grid2">
        <Field id="pf-name" label="Your name"><Input id="pf-name" value={f.name} onChange={set("name")} placeholder="Maya Chen" data-testid="profile-name-input" /></Field>
        <Field id="pf-company" label="Company"><Input id="pf-company" value={f.company} onChange={set("company")} placeholder="Lumen Labs" data-testid="profile-company-input" /></Field>
      </div>
      <Field id="pf-one" label="One-line description (optional)"><Input id="pf-one" value={f.one_liner} onChange={set("one_liner")} placeholder="Invoicing that chases late payers for you" data-testid="profile-oneliner-input" /></Field>
      <Field id="pf-web" label="Website (optional)"><Input id="pf-web" value={f.website} onChange={set("website")} placeholder="Leave blank if you don't have one yet" data-testid="profile-website-input" /></Field>
      <div className="field">
        <Label>Your goal right now</Label>
        <div className="chips" role="radiogroup">
          {GOALS.map((g) => (
            <button type="button" key={g.value} role="radio" aria-checked={f.goal === g.value}
              className={`chip ${f.goal === g.value ? "on" : ""}`} onClick={() => setF({ ...f, goal: g.value })} data-testid={`goal-chip-${g.value}`}>
              {g.label}
            </button>
          ))}
        </div>
      </div>
      <button className="btn-primary" disabled={!valid || busy} data-testid="profile-submit-button">{busy ? "Saving…" : submitLabel}</button>
    </form>
  );
};
