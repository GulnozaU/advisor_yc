import { toast } from "sonner";
import { ProfileForm } from "@/components/ProfileForm";
import { CallRow } from "@/components/RecentCalls";
import { useCalls, useMe, useApiMutation, errorText } from "@/lib/api";

const Head = ({ eyebrow, title, sub }) => (
  <header className="page-head rise">
    <p className="eyebrow">{eyebrow}</p>
    <h1 className="display sm">{title}</h1>
    {sub && <p className="muted">{sub}</p>}
  </header>
);

export function CallsPage() {
  const { data = [], isLoading } = useCalls();
  const total = data.reduce((s, c) => s + c.duration_sec, 0);
  return (
    <div className="page narrow" data-testid="calls-page">
      <Head eyebrow="History" title="Your calls" sub={data.length ? `${data.length} call${data.length === 1 ? "" : "s"} · ${Math.round(total / 60)} minutes in total` : null} />
      <section className="recent rise d1">
        {isLoading ? <div className="skeleton-card" /> : data.length === 0
          ? <div className="empty" data-testid="calls-empty">No calls yet. Start one from the dashboard.</div>
          : data.map((c) => <CallRow key={c.id} c={c} />)}
      </section>
    </div>
  );
}

export function SettingsPage() {
  const { data: me } = useMe();
  const save = useApiMutation("put", "/me", ["me"]);
  const submit = (body) => save.mutateAsync(body).then(() => toast("Profile saved")).catch((e) => toast.error(errorText(e)));
  return (
    <div className="page narrow" data-testid="settings-page">
      <Head eyebrow="Settings" title="Founder profile" sub="Your advisor uses this on every call. Email, password and account deletion live in the menu under your name." />
      <section className="panel rise d1">{me && <ProfileForm initial={me} submitLabel="Save changes" busy={save.isPending} onSubmit={submit} />}</section>
    </div>
  );
}
