"use client";

import { cn } from "@/lib/utils";

export type StepStatus = "pending" | "active" | "done" | "failed";

export type Step = {
  id: string;
  label: string;
  description?: string;
  status?: StepStatus;
};

const STEP_ICONS: Record<string, string> = {
  signal: "📡",
  constraints: "📊",
  scenarios: "💡",
  scoring: "⚖️",
  router: "🔀",
  finalizer: "✅",
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
        <div className="text-xs font-semibold text-white">Single-Purpose Agents</div>
        <div className="text-[11px] text-white/50">
          {currentStepIndex + 1} of {steps.length}
        </div>
      </div>

      <ol className="space-y-3">
        {steps.map((s, idx) => {
          const isActive = idx === currentStepIndex;
          const isDone = idx < currentStepIndex;
          const status: StepStatus = s.status ?? (isDone ? "done" : isActive ? "active" : "pending");
          const icon = STEP_ICONS[s.id] ?? "🤖";

          return (
            <li key={s.id} className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border text-sm",
                  status === "done" && "border-emerald-500/40 bg-emerald-500/15",
                  status === "active" && "border-cyan-400/50 bg-cyan-400/10",
                  status === "pending" && "border-white/15 bg-white/5",
                  status === "failed" && "border-rose-500/40 bg-rose-500/15",
                )}
              >
                {status === "done" ? (
                  <span className="text-emerald-400">✓</span>
                ) : status === "active" ? (
                  <span className="animate-pulse">{icon}</span>
                ) : (
                  <span className="opacity-50">{icon}</span>
                )}
              </div>
              <div className="flex-1">
                <div className={cn(
                  "text-xs font-semibold flex items-center gap-2",
                  isActive ? "text-cyan-200" : isDone ? "text-emerald-200" : "text-white/70"
                )}>
                  {s.label}
                  {status === "active" && (
                    <span className="inline-flex h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  )}
                </div>
                {s.description && (
                  <div className="text-[10px] text-white/40">{s.description}</div>
                )}
              </div>
              {status === "done" && (
                <span className="text-[10px] text-emerald-400/70">Complete</span>
              )}
            </li>
          );
        })}
      </ol>
      
      {/* Architecture note */}
      <div className="mt-4 pt-3 border-t border-white/10">
        <div className="text-[10px] text-white/40 text-center">
          Each agent has a single responsibility • LLM-driven orchestration
        </div>
      </div>
    </div>
  );
}

