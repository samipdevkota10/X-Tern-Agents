"use client";

import { cn } from "@/lib/utils";

export function MetricPill(props: {
  label: string;
  value: string;
  color?: "cyan" | "violet" | "amber" | "emerald" | "rose" | "muted";
  className?: string;
}) {
  const color = props.color ?? "muted";
  const colorClass =
    color === "cyan"
      ? "bg-cyan-400/10 text-cyan-200 border-cyan-400/25"
      : color === "violet"
        ? "bg-violet-400/10 text-violet-200 border-violet-400/25"
        : color === "amber"
          ? "bg-amber-500/10 text-amber-200 border-amber-500/25"
          : color === "emerald"
            ? "bg-emerald-500/10 text-emerald-200 border-emerald-500/25"
            : color === "rose"
              ? "bg-rose-500/10 text-rose-200 border-rose-500/25"
              : "bg-white/5 text-white/70 border-white/10";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium",
        "backdrop-blur-sm transition-all duration-200",
        colorClass,
        props.className,
      )}
    >
      <span className="text-white/50">{props.label}</span>
      <span className="font-semibold">{props.value}</span>
    </span>
  );
}

