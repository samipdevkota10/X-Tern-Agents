"use client";

import { cn } from "@/lib/utils";

export type StepStatus = "pending" | "active" | "done" | "failed";

export type Step = {
  id: string;
  label: string;
  status?: StepStatus;
};

export function AgentStepper(props: {
  steps: Step[];
  currentStepIndex: number;
  className?: string;
}) {
  const { steps, currentStepIndex } = props;

  return (
    <div className={cn("glass-card p-4", props.className)}>
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs font-semibold text-white">Pipeline Steps</div>
        <div className="text-[11px] text-white/50">Live status</div>
      </div>

      <ol className="space-y-3">
        {steps.map((s, idx) => {
          const isActive = idx === currentStepIndex;
          const isDone = idx < currentStepIndex;
          const status: StepStatus = s.status ?? (isDone ? "done" : isActive ? "active" : "pending");

          return (
            <li key={s.id} className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full border text-[11px] font-semibold",
                  status === "done" && "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
                  status === "active" && "border-cyan-400/50 bg-cyan-400/10 text-cyan-200",
                  status === "pending" && "border-white/15 bg-white/5 text-white/50",
                  status === "failed" && "border-rose-500/40 bg-rose-500/15 text-rose-200",
                )}
              >
                <div
                  className={cn(
                    "h-2.5 w-2.5 rounded-full",
                    status === "done" && "bg-emerald-400",
                    status === "active" && "bg-cyan-400 pulse-dot",
                    status === "pending" && "bg-white/30",
                    status === "failed" && "bg-rose-400",
                  )}
                />
              </div>
              <div className="flex-1">
                <div className={cn("text-xs font-semibold", isActive ? "text-cyan-200" : "text-white/80")}>
                  {s.label}
                </div>
                <div className="text-[11px] text-white/50 capitalize">{status}</div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

