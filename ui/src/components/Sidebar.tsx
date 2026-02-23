import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Brain,
  BookOpen,
  MessageSquare,
  KeyRound,
  Settings,
  Zap,
} from "lucide-react";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/memory", label: "Memory", icon: Brain },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
  { to: "/sessions", label: "Sessions", icon: MessageSquare },
  { to: "/api-keys", label: "API Keys", icon: KeyRound },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-56 flex flex-col border-r bg-card shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4 border-b">
        <Zap className="h-5 w-5 text-primary" />
        <span className="font-semibold tracking-tight text-sm">MemWire</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t text-xs text-muted-foreground">
        MemWire v0.1.0
      </div>
    </aside>
  );
}
