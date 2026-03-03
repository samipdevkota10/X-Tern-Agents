"use client";

import { cn } from "@/lib/utils";

type SeverityLevel = "critical" | "high" | "medium" | "low";

export function SeverityBadge(props: {
  severity: number | SeverityLevel;
  className?: string;
}) {
  const { className } = props;
  const mapped = mapSeverity(props.severity);
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
        "backdrop-blur-sm transition-all duration-200",
        mapped.className,
        className,
      )}
      title={mapped.label}
    >
      {mapped.label}
    </span>
  );
}

function mapSeverity(severity: number | SeverityLevel): {
  label: string;
  className: string;
} {
  if (typeof severity === "number") {
    if (severity >= 5)
      return {
        label: "S5 Critical",
        className: "bg-rose-500/20 text-rose-200 border-rose-500/40",
      };
    if (severity === 4)
      return {
        label: "S4 High",
        className: "bg-amber-500/20 text-amber-200 border-amber-500/40",
      };
    if (severity === 3)
      return {
        label: "S3 Medium",
        className: "bg-violet-400/20 text-violet-200 border-violet-400/40",
      };
    if (severity === 2)
      return {
        label: "S2 Low",
        className: "bg-cyan-400/15 text-cyan-200 border-cyan-400/30",
      };
    return {
      label: "S1 Low",
      className: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
    };
  }

  switch (severity) {
    case "critical":
      return {
        label: "Critical",
        className: "bg-rose-500/20 text-rose-200 border-rose-500/40",
      };
    case "high":
      return {
        label: "High",
        className: "bg-amber-500/20 text-amber-200 border-amber-500/40",
      };
    case "medium":
      return {
        label: "Medium",
        className: "bg-violet-400/20 text-violet-200 border-violet-400/40",
      };
    case "low":
    default:
      return {
        label: "Low",
        className: "bg-emerald-500/15 text-emerald-200 border-emerald-500/30",
      };
  }
}

