"use client";

import { usePathname, useRouter } from "next/navigation";
import { Bell, Play } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { usePendingApprovalsCount } from "@/hooks/useScenarios";

function getTitle(pathname: string) {
  if (pathname.startsWith("/dashboard")) return "Operations Overview";
  if (pathname.startsWith("/disruptions")) return "Disruptions Inbox";
  if (pathname.startsWith("/scenarios")) return "Scenario Comparison";
  if (pathname.startsWith("/approvals")) return "Approval Queue";
  if (pathname.startsWith("/audit")) return "Audit Log";
  if (pathname.startsWith("/run")) return "Run Planner";
  if (pathname.startsWith("/login")) return "Sign In";
  return "DisruptIQ";
}

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const approvalsCount = usePendingApprovalsCount();

  return (
    <header className="fixed left-60 right-0 top-0 z-20 h-14 border-b border-white/10 bg-black/30 backdrop-blur-lg">
      <div className="flex h-full items-center justify-between px-6">
        <div>
          <div className="text-sm font-semibold text-white">{getTitle(pathname)}</div>
          <div className="text-[11px] text-white/50">AI-native disruption response workspace.</div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/approvals")}
            className="relative h-9 w-9 rounded-full border border-white/10 bg-white/5 text-white/70 hover:bg-white/10 hover:text-white transition-all duration-200 flex items-center justify-center"
            aria-label="Approvals"
          >
            <Bell className="h-4 w-4" />
            {approvalsCount > 0 ? (
              <span className="absolute -right-1 -top-1 min-w-4 h-4 rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white flex items-center justify-center shadow-[0_0_20px_rgba(244,63,94,0.55)]">
                {approvalsCount}
              </span>
            ) : null}
          </button>

          <Button
            size="sm"
            onClick={() => router.push("/run")}
            className={cn(
              "rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300",
              "shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200",
            )}
          >
            <Play className="mr-1 h-4 w-4" />
            Run Pipeline
          </Button>
        </div>
      </div>
    </header>
  );
}

