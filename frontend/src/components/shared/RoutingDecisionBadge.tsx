"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowRight, Sparkles } from "lucide-react";

interface RoutingDecisionBadgeProps {
  llmSuggested?: string;
  finalDecision: string;
  overrideReason?: string;
  confidence?: number;
  className?: string;
}

function formatStepName(step: string): string {
  return step
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function RoutingDecisionBadge({
  llmSuggested,
  finalDecision,
  overrideReason,
  confidence,
  className,
}: RoutingDecisionBadgeProps) {
  const wasOverridden = overrideReason && llmSuggested && llmSuggested !== finalDecision;

  if (wasOverridden) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 px-2 py-1 rounded-md bg-amber-500/10 border border-amber-500/30",
          className
        )}
      >
        <AlertTriangle className="h-3 w-3 text-amber-400" />
        <div className="flex items-center gap-1 text-[10px]">
          <span className="text-amber-300/70 line-through">
            {formatStepName(llmSuggested)}
          </span>
          <ArrowRight className="h-2.5 w-2.5 text-white/50" />
          <span className="text-amber-200 font-medium">
            {formatStepName(finalDecision)}
          </span>
        </div>
        <span className="text-[9px] text-amber-400/70 ml-1">
          (guardrail)
        </span>
      </div>
    );
  }

  // LLM-driven decision (no override)
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/30",
        className
      )}
    >
      <Sparkles className="h-3 w-3 text-cyan-400" />
      <span className="text-[10px] text-cyan-200">
        LLM → {formatStepName(finalDecision)}
      </span>
      {confidence !== undefined && (
        <span
          className={cn(
            "text-[9px] px-1 rounded",
            confidence >= 0.8
              ? "text-emerald-300"
              : confidence >= 0.5
              ? "text-amber-300"
              : "text-rose-300"
          )}
        >
          {Math.round(confidence * 100)}%
        </span>
      )}
    </div>
  );
}
