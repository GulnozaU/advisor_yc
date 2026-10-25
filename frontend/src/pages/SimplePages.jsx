import { Mail, CalendarDays } from "lucide-react";
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

const CONNECTIONS = [
  { id: "gmail", icon: Mail, name: "Gmail", body: "Reads your inbox to find replies you owe and drafts them for you." },
  { id: "calendar", icon: CalendarDays, name: "Google Calendar", body: "Looks at your week so priorities fit around your meetings." },
];

export function ConnectionsPage() {
  return (
    <div className="page narrow" data-testid="connections-page">
      <Head eyebrow="Connections" title="Bring in your real work" sub="For now your priorities are typed in by you. These connections will fill the list for you." />
      <div className="conn-list rise d1">
        {CONNECTIONS.map(({ id, icon: Icon, name, body }) => (
          <div key={id} className="conn" data-testid={`connection-${id}`}>
            <span className="conn-icon"><Icon size={20} /></span>
            <div><p className="conn-name">{name}</p><p className="muted small">{body}</p></div>
            <span className="conn-status" data-testid={`connection-${id}-status`}>Coming with the team pipeline</span>
          </div>
        ))}
      </div>
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
