"use client";

import type { DecisionType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function DecisionBadge(props: { decision: DecisionType | string; className?: string }) {
  const d = props.decision;
  const mapped = mapDecision(d);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
        "backdrop-blur-sm transition-all duration-200",
        mapped.className,
        props.className,
      )}
      title={mapped.label}
    >
      {mapped.label}
    </span>
  );
}

function mapDecision(decision: DecisionType | string): { label: string; className: string } {
  switch (decision) {
    case "approved":
      return {
        label: "Approved",
        className: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
      };
    case "rejected":
      return {
        label: "Rejected",
        className: "bg-rose-500/15 text-rose-200 border-rose-500/30",
      };
    case "edited":
      return {
        label: "Edited",
        className: "bg-cyan-400/15 text-cyan-200 border-cyan-400/30",
      };
    case "pending":
      return {
        label: "Pending",
        className: "bg-amber-500/15 text-amber-200 border-amber-500/30",
      };
    default:
      return {
        label: String(decision),
        className: "bg-white/10 text-white/70 border-white/15",
      };
  }
}

