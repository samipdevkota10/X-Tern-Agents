"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, Star } from "lucide-react";

import type { Scenario } from "@/lib/types";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/shared/GlassCard";
import { ActionTypeBadge } from "@/components/shared/ActionTypeBadge";
import { MetricPill } from "@/components/shared/MetricPill";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export function ScenarioCard(props: {
  scenario: Scenario & { order_priority?: string };
  recommended?: boolean;
  isManager: boolean;
  onApprove: (note: string) => Promise<void>;
  onReject: (note: string) => Promise<void>;
}) {
  const { scenario, isManager, recommended } = props;
  const [expanded, setExpanded] = React.useState(false);
  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState<"approve" | "reject" | null>(null);

  const score = scenario.score_json ?? {};
  const plan = scenario.plan_json ?? {};
  
  // Safe score values with defaults
  const costImpact = score.cost_impact_usd ?? 0;
  const slaRisk = score.sla_risk ?? 0;
  const laborMinutes = score.labor_impact_minutes ?? 0;

  // Check if LLM was used for this scenario
  const isLLMGenerated = Boolean(scenario.llm_rationale || scenario.used_llm);
  
  // Get the summary to display - prefer summary field, then llm_rationale, then generic
  const summary =
    typeof plan.summary === "string" && plan.summary.trim().length > 0
      ? plan.summary
      : typeof scenario.llm_rationale === "string" && scenario.llm_rationale.trim().length > 0
      ? scenario.llm_rationale
      : typeof plan.rationale === "string" && plan.rationale.trim().length > 0
      ? plan.rationale
      : "Recommendation based on disruption constraints and SLA/cost tradeoffs.";
  
  const reasoningSourceLabel = isLLMGenerated
    ? "AI Reasoning (AWS Bedrock + RAG)"
    : "Rule-based Analysis";

  const approve = async () => {
    setBusy("approve");
    try {
      await props.onApprove(note || "Approved in DisruptIQ");
    } finally {
      setBusy(null);
    }
  };

  const reject = async () => {
    setBusy("reject");
    try {
      await props.onReject(note || "Rejected in DisruptIQ");
    } finally {
      setBusy(null);
    }
  };

  return (
    <GlassCard
      className={cn(
        "p-4 flex flex-col gap-3",
        recommended && "shadow-[0_0_20px_rgba(34,211,238,0.3)] ring-1 ring-cyan-400/40",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ActionTypeBadge action={scenario.action_type} />
            {recommended && (
              <span className="inline-flex items-center gap-1 rounded-full bg-cyan-400/15 px-2 py-0.5 text-[10px] font-semibold text-cyan-200 shadow-[0_0_20px_rgba(34,211,238,0.25)]">
                <Star className="h-3 w-3 fill-cyan-300 text-cyan-300" />
                Recommended
              </span>
            )}
          </div>
          <div className="text-sm font-semibold text-white">
            Order <span className="font-mono">{scenario.order_id}</span>
          </div>
          <div className="text-[11px] text-white/50">
            Status: <span className="text-white/70">{scenario.status}</span>
            {scenario.order_priority ? (
              <>
                {" "}
                • Priority: <span className="text-white/70">{scenario.order_priority}</span>
              </>
            ) : null}
          </div>
        </div>

        <div className="flex flex-col items-end gap-1.5">
          <MetricPill label="Cost" value={`$${costImpact.toFixed(0)}`} color="amber" />
          <MetricPill label="SLA" value={`${(slaRisk * 100).toFixed(1)}%`} color="rose" />
          <MetricPill
            label="Labor"
            value={`${(laborMinutes / 60).toFixed(1)}h`}
            color="emerald"
          />
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider",
            isLLMGenerated
              ? "bg-violet-500/20 text-violet-300 ring-1 ring-violet-400/30"
              : "bg-slate-500/20 text-slate-300 ring-1 ring-slate-400/30"
          )}>
            {isLLMGenerated ? "🤖 LLM" : "📐 Rules"}
          </span>
          <span className="text-[10px] text-white/40">{reasoningSourceLabel}</span>
        </div>
        <div className="text-xs text-white/70 line-clamp-3">{summary}</div>
      </div>

      <div className="flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-[11px] text-cyan-200/80 hover:text-cyan-200 transition-all duration-200 inline-flex items-center gap-1"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? "Hide full plan" : "View full plan"}
        </button>

        <TooltipProvider>
          <div className="flex items-center gap-2">
            {isManager ? (
              <>
                <Button
                  size="sm"
                  className="h-8 rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all duration-200"
                  onClick={approve}
                  disabled={busy !== null || scenario.status !== "pending"}
                >
                  {busy === "approve" ? "Approving…" : "Approve"}
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  className="h-8 rounded-full transition-all duration-200"
                  onClick={reject}
                  disabled={busy !== null || scenario.status !== "pending"}
                >
                  {busy === "reject" ? "Rejecting…" : "Reject"}
                </Button>
              </>
            ) : (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button size="sm" className="h-8 rounded-full" disabled>
                      Approve
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Manager approval required</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button size="sm" variant="destructive" className="h-8 rounded-full" disabled>
                      Reject
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Manager approval required</TooltipContent>
                </Tooltip>
              </>
            )}
          </div>
        </TooltipProvider>
      </div>

      {expanded ? (
        <div className="mt-2 space-y-3">
          <div className="text-[11px] text-white/50">Optional note (used for approval/rejection):</div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add a short note…"
            className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-white/80 placeholder:text-white/30 outline-none focus:border-cyan-400/40 transition-all duration-200"
            rows={2}
          />
          
          {/* Human-readable plan display */}
          {plan.summary || plan.what_happened || plan.what_to_do || plan.how_to_handle ? (
            <div className="space-y-3">
              {plan.summary && (
                <div className="rounded-lg bg-cyan-500/10 border border-cyan-400/20 p-3">
                  <div className="text-[10px] font-semibold text-cyan-300 uppercase tracking-wider mb-1">Summary</div>
                  <div className="text-sm text-white/90">{plan.summary}</div>
                </div>
              )}
              
              {plan.what_happened && (
                <div className="rounded-lg bg-amber-500/10 border border-amber-400/20 p-3">
                  <div className="text-[10px] font-semibold text-amber-300 uppercase tracking-wider mb-1">What Happened</div>
                  <div className="text-xs text-white/80">{plan.what_happened}</div>
                </div>
              )}
              
              {plan.what_to_do && (
                <div className="rounded-lg bg-emerald-500/10 border border-emerald-400/20 p-3">
                  <div className="text-[10px] font-semibold text-emerald-300 uppercase tracking-wider mb-1">What to Do</div>
                  <div className="text-xs text-white/80">{plan.what_to_do}</div>
                </div>
              )}
              
              {plan.how_to_handle && (
                <div className="rounded-lg bg-violet-500/10 border border-violet-400/20 p-3">
                  <div className="text-[10px] font-semibold text-violet-300 uppercase tracking-wider mb-1">How to Handle</div>
                  <div className="text-xs text-white/80 whitespace-pre-line">{plan.how_to_handle}</div>
                </div>
              )}
            </div>
          ) : (
            <div className="code-block max-h-64 overflow-auto">
              <pre className="whitespace-pre-wrap">{JSON.stringify(plan, null, 2)}</pre>
            </div>
          )}
        </div>
      ) : null}
    </GlassCard>
  );
}

