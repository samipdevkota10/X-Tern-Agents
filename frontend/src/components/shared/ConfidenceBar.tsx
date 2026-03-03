"use client";

import { cn } from "@/lib/utils";

export function ConfidenceBar(props: { score: number; className?: string }) {
  const s = clamp(props.score, 0, 1);
  const pct = Math.round(s * 100);
  const gradient =
    s >= 0.75
      ? "from-emerald-500 to-cyan-400"
      : s >= 0.45
        ? "from-amber-500 to-cyan-400"
        : "from-rose-500 to-amber-500";

  return (
    <div className={cn("space-y-1", props.className)}>
      <div className="flex items-center justify-between text-[11px] text-white/50">
        <span>Confidence</span>
        <span className="font-mono text-white/70">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className={cn("h-full rounded-full bg-gradient-to-r transition-all duration-200", gradient)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

