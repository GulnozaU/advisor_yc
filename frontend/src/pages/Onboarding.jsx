import { useNavigate } from "react-router-dom";
import { useUser } from "@clerk/react";
import { toast } from "sonner";
import { ProfileForm } from "@/components/ProfileForm";
import { useApiMutation, errorText } from "@/lib/api";

export default function Onboarding() {
  const nav = useNavigate();
  const { user } = useUser();
  const save = useApiMutation("put", "/me", ["me", "priorities"]);
  const submit = (body) => save.mutateAsync(body).then(() => nav("/dashboard", { replace: true })).catch((e) => toast.error(errorText(e)));

  return (
    <div className="onboard" data-testid="onboarding-page">
      <div className="onboard-card rise">
        <p className="eyebrow">Step 1 of 1 · under a minute</p>
        <h1 className="display sm">Tell your advisor who you are.</h1>
        <p className="muted">This is what it knows when it picks up. You can change it any time in Settings.</p>
        <ProfileForm initial={{ name: user?.firstName ? user.fullName || user.firstName : "" }} submitLabel="Open my dashboard" busyLabel="Researching your startup…" busy={save.isPending} onSubmit={submit} />
      </div>
    </div>
  );
}
