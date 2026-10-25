import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { Show, UserButton } from "@clerk/react";
import { useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, PhoneCall, History, Plug, Settings } from "lucide-react";
import { endGuest } from "@/lib/api";

const GuestBar = () => {
  const nav = useNavigate();
  const qc = useQueryClient();
  const exit = async () => { await endGuest(); qc.clear(); nav("/"); };
  return (
    <div className="guest-bar" data-testid="guest-bar">
      <span>You're trying the demo as Carl Walker at Fernhill Finance.</span>
      <Link to="/sign-up" className="link" data-testid="guest-signup-link">Sign up to use your own inbox</Link>
      <button className="link-btn" onClick={exit} data-testid="guest-exit-button">Exit demo</button>
    </div>
  );
};

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { to: "/call", label: "Call", icon: PhoneCall },
  { to: "/calls", label: "Calls", icon: History },
  { to: "/connections", label: "Connections", icon: Plug },
  { to: "/settings", label: "Settings", icon: Settings },
];

export const AppShell = () => (
  <div className="shell">
    <aside className="sidebar" data-testid="app-sidebar">
      <div className="brand"><b>Advisor</b> on Call</div>
      <nav className="nav">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className="nav-link" data-testid={`nav-${label.toLowerCase()}`}>
            <Icon size={18} strokeWidth={1.75} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-user" data-testid="user-menu"><Show when="signed-in"><UserButton showName /></Show></div>
    </aside>
    <div className="mobile-top">
      <div className="brand"><b>Advisor</b> on Call</div>
      <Show when="signed-in"><UserButton /></Show>
    </div>
    <main className="shell-main"><Show when="signed-out"><GuestBar /></Show><Outlet /></main>
  </div>
);
