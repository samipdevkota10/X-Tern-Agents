"use client";

import type { ScenarioActionType } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ActionTypeBadge(props: {
  action: ScenarioActionType | string;
  className?: string;
}) {
  const a = props.action;
  const mapped = mapAction(a);
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

function mapAction(action: ScenarioActionType | string): { label: string; className: string } {
  switch (action) {
    case "delay":
      return {
        label: "Delay",
        className: "bg-amber-500/15 text-amber-200 border-amber-500/30",
      };
    case "reroute":
      return {
        label: "Reroute",
        className: "bg-violet-400/15 text-violet-200 border-violet-400/30",
      };
    case "substitute":
      return {
        label: "Substitute",
        className: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
      };
    case "resequence":
      return {
        label: "Resequence",
        className: "bg-cyan-400/15 text-cyan-200 border-cyan-400/30",
      };
    case "expedite":
      return {
        label: "Expedite",
        className: "bg-rose-500/15 text-rose-200 border-rose-500/30",
      };
    case "split":
      return {
        label: "Split",
        className: "bg-sky-500/15 text-sky-200 border-sky-500/30",
      };
    default:
      return {
        label: String(action),
        className: "bg-white/10 text-white/70 border-white/15",
      };
  }
}

