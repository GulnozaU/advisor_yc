import { Navigate } from "react-router-dom";
import { Show } from "@clerk/react";
import { useMe } from "@/lib/api";

const Loading = () => <div className="page-loading" data-testid="page-loading"><span className="loader" /></div>;

const NeedsProfile = ({ children, onboarding }) => {
  const { data, isLoading, isError } = useMe();
  if (isLoading) return <Loading />;
  if (isError) return <div className="page-loading">Couldn't load your profile. Refresh to try again.</div>;
  if (!onboarding && !data.onboarded) return <Navigate to="/onboarding" replace />;
  if (onboarding && data.onboarded) return <Navigate to="/dashboard" replace />;
  return children;
};

export const Protected = ({ children, onboarding = false }) => (
  <>
    <Show when="signed-in"><NeedsProfile onboarding={onboarding}>{children}</NeedsProfile></Show>
    <Show when="signed-out"><Navigate to="/" replace /></Show>
  </>
);
