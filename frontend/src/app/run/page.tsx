"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Play, RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useRequireAuth } from "@/lib/auth";
import type { Disruption, PipelineRunStatus } from "@/lib/types";
import { runPipeline } from "@/lib/api";
import { useDisruptions } from "@/hooks/useDisruptions";
import { usePipelineStatus } from "@/hooks/usePipelineStatus";

import { GlassCard } from "@/components/shared/GlassCard";
import { AgentStepper } from "@/components/shared/AgentStepper";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STEPS = [
  { id: "signal", label: "Signal Intake" },
  { id: "constraints", label: "Constraint Builder" },
  { id: "scenarios", label: "Scenario Generator" },
  { id: "scoring", label: "Tradeoff Scoring" },
];

function stepIndexFromStatus(s: PipelineRunStatus | null): number {
  if (!s) return 0;
  const step = (s.current_step ?? "").toLowerCase();
  if (step.includes("signal")) return 0;
  if (step.includes("constraint")) return 1;
  if (step.includes("scenario")) return 2;
  if (step.includes("score")) return 3;
  if (s.status === "done") return 3;
  return Math.max(0, Math.min(3, Math.floor((s.progress ?? 0) * 4)));
}

export default function RunPage() {
  useRequireAuth();
  const router = useRouter();

  const disruptions = useDisruptions({ status: "open" });
  const [selected, setSelected] = React.useState<string>("");
  const [manual, setManual] = React.useState<string>("");
  const [runId, setRunId] = React.useState<string | null>(null);
  const [starting, setStarting] = React.useState(false);

  const status = usePipelineStatus(runId);
  const currentIdx = stepIndexFromStatus(status.status);

  const effectiveDisruptionId = manual.trim() || selected;

  const startRun = async () => {
    if (!effectiveDisruptionId) {
      toast.error("Select an active disruption or enter an ID.");
      return;
    }
    setStarting(true);
    try {
      const res = await runPipeline(effectiveDisruptionId);
      setRunId(res.pipeline_run_id);
      toast.success("Pipeline started.");
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to start pipeline");
    } finally {
      setStarting(false);
    }
  };

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
                <SelectContent>
                  {disruptions.disruptions.map((d: Disruption) => (
                    <SelectItem key={d.id} value={d.id}>
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

            {runId ? (
              <div className="text-[11px] text-white/50">
                Run ID: <span className="font-mono text-white/70">{runId}</span>
              </div>
            ) : null}
          </div>

          <AgentStepper
            steps={STEPS.map((s) => ({ id: s.id, label: s.label }))}
            currentStepIndex={currentIdx}
          />
        </div>

        {status.status ? (
          status.status.status === "done" ? (
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
                  onClick={() => router.push("/scenarios")}
                  className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)]"
                >
                  View Scenarios
                </Button>
              </div>
            </GlassCard>
          ) : status.status.status === "failed" ? (
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

