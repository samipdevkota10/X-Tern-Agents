"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Play, RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useRequireAuth } from "@/lib/auth";
import type { Disruption, PipelineRunStatus } from "@/lib/types";
import { startPipeline } from "@/lib/api";
import { useDisruptions } from "@/hooks/useDisruptions";
import {
  usePipelineStatus,
  setStoredPipelineRunId,
  clearStoredPipelineRunId,
  getStoredPipelineRunId,
} from "@/hooks/usePipelineStatus";
import { useAgentActivity } from "@/hooks/useAgentActivity";

import { GlassCard } from "@/components/shared/GlassCard";
import { AgentStepper } from "@/components/shared/AgentStepper";
import { AgentActivityLog } from "@/components/shared/AgentActivityLog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STEPS = [
  { id: "signal", label: "Signal Intake", description: "Identifies impacted orders" },
  { id: "constraints", label: "Constraint Builder", description: "Gathers operational context" },
  { id: "scenarios", label: "Scenario Generator", description: "Creates response options" },
  { id: "scoring", label: "Tradeoff Scoring", description: "Ranks by cost/risk" },
  { id: "router", label: "Router", description: "LLM-driven orchestration" },
];

function stepIndexFromStatus(s: PipelineRunStatus | null): number {
  if (!s) return 0;
  const step = (s.current_step ?? "").toLowerCase();
  if (step.includes("signal")) return 0;
  if (step.includes("constraint")) return 1;
  if (step.includes("scenario")) return 2;
  if (step.includes("score") || step.includes("tradeoff")) return 3;
  if (step.includes("router") || step.includes("supervisor")) return 4;
  if (step.includes("finalize") || s.status === "completed") return 4;
  return Math.max(0, Math.min(4, Math.floor((s.progress ?? 0) * 5)));
}

export default function RunPage() {
  useRequireAuth();
  const router = useRouter();

  const disruptions = useDisruptions({ status: "open" });
  const [selected, setSelected] = React.useState<string>("");
  const [manual, setManual] = React.useState<string>("");
  const [runId, setRunId] = React.useState<string | null>(null);
  const [starting, setStarting] = React.useState(false);

  // Restore stored run ID after mount to avoid hydration mismatch (localStorage only exists on client)
  React.useEffect(() => {
    const stored = getStoredPipelineRunId();
    if (stored) setRunId(stored);
  }, []);

  const status = usePipelineStatus(runId);
  const currentIdx = stepIndexFromStatus(status.status);
  const isRunning =
    status.status?.status === "running" ||
    status.status?.status === "queued" ||
    status.status?.status === "pending";
  const isComplete =
    status.status?.status === "done" ||
    status.status?.status === "needs_review" ||
    status.status?.status === "completed";
  const isFailed = status.status?.status === "failed";
  const activity = useAgentActivity(status.runId ?? runId, isRunning);
  const [showActivityLog, setShowActivityLog] = React.useState(true);

  // Extract routing trace from final summary
  const routingTrace = (status.status?.final_summary_json?.routing_trace as Array<{
    ts: string;
    from: string;
    llm_next: string | null;
    final: string;
    override: string | null;
    confidence: number | null;
    reason: string | null;
  }>) ?? [];

  const effectiveDisruptionId = manual.trim() || selected;

  const startRun = async () => {
    if (!effectiveDisruptionId) {
      toast.error("Select an active disruption or enter an ID.");
      return;
    }
    setStarting(true);
    try {
      const res = await startPipeline(effectiveDisruptionId);
      setRunId(res.pipeline_run_id);
      setStoredPipelineRunId(res.pipeline_run_id);
      toast.success("Pipeline started. It will continue in the background if you switch tabs.");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to start pipeline");
    } finally {
      setStarting(false);
    }
  };

  // Toast when pipeline completes (works even if user switched tabs and came back)
  const prevStatusRef = React.useRef<string | undefined>(undefined);
  React.useEffect(() => {
    const s = status.status?.status;
    const wasRunning =
      prevStatusRef.current === "running" ||
      prevStatusRef.current === "queued" ||
      prevStatusRef.current === "pending";
    if (s === "done" || s === "needs_review" || s === "completed") {
      if (wasRunning) {
        const count = (status.status?.final_summary_json as Record<string, unknown>)
          ?.scenarios_count as number | undefined;
        toast.success(
          `Pipeline complete! ${typeof count === "number" ? `${count} scenarios` : "Scenarios"} generated.`,
          { duration: 5000 }
        );
        clearStoredPipelineRunId();
      }
      prevStatusRef.current = s;
    } else if (s === "failed") {
      if (wasRunning) {
        toast.error("Pipeline failed. Check the Run Planner for details.");
        clearStoredPipelineRunId();
      }
      prevStatusRef.current = s;
    } else {
      prevStatusRef.current = s;
    }
  }, [status.status?.status, status.status?.final_summary_json]);

  const summary = (status.status?.final_summary_json ?? {}) as Record<string, unknown>;
  const scenariosCount = typeof summary.scenarios_count === "number" ? summary.scenarios_count : null;
  const approvalQueueCount = typeof summary.approval_queue_count === "number" ? summary.approval_queue_count : null;

  return (
    <div className="flex items-center justify-center">
      <GlassCard glow className="w-full max-w-3xl p-6 space-y-5">
        <div>
          <div className="text-sm font-semibold text-white">Run Planner</div>
          <div className="text-[11px] text-white/50">Trigger the pipeline and watch step-by-step progress.</div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-white/60 mb-1">Active disruption</div>
              <Select value={selected} onValueChange={setSelected}>
                <SelectTrigger className="h-9 border-white/10 bg-black/30 text-white/80">
                  <SelectValue placeholder={disruptions.isLoading ? "Loading…" : "Select disruption"} />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/20">
                  {disruptions.disruptions.map((d: Disruption) => (
                    <SelectItem key={d.id} value={d.id} className="text-white/90 focus:bg-slate-800 focus:text-white">
                      {d.type} • S{d.severity} • {d.id.slice(0, 10)}…
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="text-[11px] text-white/60 mb-1">Or manual ID</div>
              <Input
                value={manual}
                onChange={(e) => setManual(e.target.value)}
                placeholder="disruption_id"
                className="h-9 bg-black/30 border-white/10 text-white/80 placeholder:text-white/30"
              />
            </div>

            <Button
              onClick={startRun}
              disabled={starting}
              className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200"
            >
              <Play className="mr-1 h-4 w-4" />
              {starting ? "Starting…" : "Run Pipeline"}
            </Button>

            {(runId || status.runId) ? (
              <div className="text-[11px] text-white/50">
                Run ID: <span className="font-mono text-white/70">{runId || status.runId}</span>
              </div>
            ) : null}
          </div>

          <AgentStepper
            steps={STEPS.map((s) => ({ id: s.id, label: s.label, description: s.description }))}
            currentStepIndex={currentIdx}
          />
        </div>

        {/* Agent Activity Log */}
        {(runId || status.runId) && (
          <div className="space-y-2">
            <button
              onClick={() => setShowActivityLog(!showActivityLog)}
              className="flex items-center gap-2 text-xs text-white/70 hover:text-white/90 transition-colors"
            >
              {showActivityLog ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
              <span>Agent Activity Details</span>
              {activity.logs.length > 0 && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300">
                  {activity.logs.length}
                </span>
              )}
            </button>
            {showActivityLog && (
              <AgentActivityLog
                logs={activity.logs}
                routingTrace={routingTrace}
                isRunning={isRunning}
                expanded={isComplete}
              />
            )}
          </div>
        )}

        {status.status ? (
          isComplete ? (
            <GlassCard className="p-4 border border-emerald-500/25 bg-emerald-500/10">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-300" />
                  <div>
                    <div className="text-sm font-semibold text-white">Pipeline complete</div>
                    <div className="text-xs text-white/60">
                      Scenarios generated: <span className="text-white/80">{scenariosCount ?? "—"}</span> • Need approval:{" "}
                      <span className="text-white/80">{approvalQueueCount ?? "—"}</span>
                    </div>
                  </div>
                </div>
                <Button
                  onClick={() => {
                    const disruptionId = status.status?.disruption_id;
                    router.push(disruptionId ? `/scenarios?disruption_id=${disruptionId}` : "/scenarios");
                  }}
                  className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)]"
                >
                  View Scenarios
                </Button>
              </div>
            </GlassCard>
          ) : isFailed ? (
            <GlassCard className="p-4 border border-rose-500/25 bg-rose-500/10">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-rose-300" />
                <div className="flex-1">
                  <div className="text-sm font-semibold text-white">Pipeline failed</div>
                  <div className="text-xs text-white/60 mt-1">
                    {status.status.error_message ?? "Unknown error"}
                  </div>
                  <Button
                    onClick={startRun}
                    className="mt-3 rounded-full bg-white/5 text-white hover:bg-white/10 transition-all duration-200"
                    variant="outline"
                  >
                    <RefreshCcw className="mr-1 h-4 w-4" />
                    Retry
                  </Button>
                </div>
              </div>
            </GlassCard>
          ) : (
            <div className="text-xs text-white/60">
              Status: <span className="text-white/80">{status.status.status}</span> • Step:{" "}
              <span className="text-white/80">{status.status.current_step ?? "—"}</span> • Progress:{" "}
              <span className="text-cyan-200">{Math.round((status.status.progress ?? 0) * 100)}%</span>
            </div>
          )
        ) : null}
      </GlassCard>
    </div>
  );
}

