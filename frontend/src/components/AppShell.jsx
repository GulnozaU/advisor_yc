import { NavLink, Outlet } from "react-router-dom";
import { UserButton } from "@clerk/react";
import { LayoutGrid, PhoneCall, History, Plug, Settings } from "lucide-react";

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
      <div className="sidebar-user" data-testid="user-menu"><UserButton showName /></div>
    </aside>
    <div className="mobile-top">
      <div className="brand"><b>Advisor</b> on Call</div>
      <UserButton />
    </div>
    <main className="shell-main"><Outlet /></main>
  </div>
);
