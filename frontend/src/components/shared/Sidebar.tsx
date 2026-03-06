"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  History,
  LayoutDashboard,
  LogOut,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { usePendingApprovalsCount } from "@/hooks/useScenarios";
import { Badge } from "@/components/ui/badge";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  managerOnly?: boolean;
};

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/disruptions", label: "Disruptions", icon: AlertTriangle },
  { href: "/scenarios", label: "Scenarios", icon: Sparkles },
  { href: "/approved", label: "Approved Actions", icon: CheckCircle2 },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck, managerOnly: true },
  { href: "/audit", label: "Audit Log", icon: History },
  { href: "/run", label: "Run Planner", icon: ClipboardList },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, role, isManager, logout } = useAuth();
  const approvalsCount = usePendingApprovalsCount();

  return (
    <aside className="fixed left-0 top-0 z-30 h-screen w-60 border-r border-white/10 bg-black/30 backdrop-blur-lg">
      <div className="flex h-full flex-col px-4 py-5">
        <div className="mb-6">
          <div className="text-sm font-semibold text-white">
            Disrupt<span className="text-cyan-200">IQ</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-white/40">
            Enterprise Control Tower
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-auto pr-1">
          {NAV.filter((i) => (i.managerOnly ? isManager : true)).map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex items-center justify-between rounded-xl px-3 py-2 text-xs font-medium",
                  "transition-all duration-200",
                  active
                    ? "bg-cyan-400/15 text-cyan-200 shadow-[0_0_20px_rgba(34,211,238,0.25)]"
                    : "text-white/60 hover:bg-white/10 hover:text-white",
                )}
              >
                <span className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>

                {item.href === "/approvals" && approvalsCount > 0 ? (
                  <span className="rounded-full bg-rose-500/80 px-2 py-0.5 text-[10px] font-bold text-white shadow-[0_0_20px_rgba(244,63,94,0.4)]">
                    {approvalsCount}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-4 border-t border-white/10 pt-4">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-400 text-slate-950 font-bold flex items-center justify-center">
              {user?.username?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold text-white">
                {user?.username ?? "Unknown"}
              </div>
              <div className="text-[11px] text-white/50">{role ?? "—"}</div>
            </div>
            {role ? (
              <Badge className="border border-white/10 bg-white/5 text-white/70" variant="outline">
                {role === "warehouse_manager" ? "Manager" : "Analyst"}
              </Badge>
            ) : null}
          </div>

          <button
            type="button"
            onClick={logout}
            className="mt-3 w-full rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-white/70 hover:bg-rose-500/15 hover:text-rose-100 transition-all duration-200 inline-flex items-center justify-center gap-2"
          >
            <LogOut className="h-3.5 w-3.5" />
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}

