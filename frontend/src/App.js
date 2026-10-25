import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Show } from "@clerk/react";
import { Toaster } from "@/components/ui/sonner";
import ClerkAuthProvider from "@/components/auth/ClerkAuthProvider";
import { AppShell } from "@/components/AppShell";
import { Protected } from "@/components/Guards";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Onboarding from "@/pages/Onboarding";
import Dashboard from "@/pages/Dashboard";
import CallPage from "@/pages/CallPage";
import { CallsPage, SettingsPage } from "@/pages/SimplePages";
import ConnectionsPage from "@/pages/ConnectionsPage";

const Home = () => (
  <>
    <Show when="signed-in"><Navigate to="/dashboard" replace /></Show>
    <Show when="signed-out"><Landing /></Show>
  </>
);

export default function App() {
  return (
    <BrowserRouter>
      <ClerkAuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sign-in/*" element={<AuthPage mode="sign-in" />} />
          <Route path="/sign-up/*" element={<AuthPage mode="sign-up" />} />
          <Route path="/onboarding" element={<Protected onboarding><Onboarding /></Protected>} />
          <Route element={<Protected><AppShell /></Protected>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/call" element={<CallPage />} />
            <Route path="/calls" element={<CallsPage />} />
            <Route path="/connections" element={<ConnectionsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster position="bottom-right" />
      </ClerkAuthProvider>
    </BrowserRouter>
  );
}
