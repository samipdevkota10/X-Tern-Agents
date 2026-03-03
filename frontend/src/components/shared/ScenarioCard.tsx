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

  const score = scenario.score_json;
  const plan = scenario.plan_json ?? {};

  const rationale =
    typeof plan.rationale === "string" && plan.rationale.trim().length > 0
      ? plan.rationale
      : "Deterministic recommendation based on disruption constraints and SLA/cost tradeoffs.";

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
          <MetricPill label="Cost" value={`$${score.cost_impact_usd.toFixed(0)}`} color="amber" />
          <MetricPill label="SLA" value={`${(score.sla_risk * 100).toFixed(1)}%`} color="rose" />
          <MetricPill
            label="Labor"
            value={`${(score.labor_impact_minutes / 60).toFixed(1)}h`}
            color="emerald"
          />
        </div>
      </div>

      <div className="text-xs text-white/70 line-clamp-2">{rationale}</div>

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
        <div className="mt-2 space-y-2">
          <div className="text-[11px] text-white/50">Optional note (used for approval/rejection):</div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Add a short note…"
            className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-xs text-white/80 placeholder:text-white/30 outline-none focus:border-cyan-400/40 transition-all duration-200"
            rows={2}
          />
          <div className="code-block max-h-64 overflow-auto">
            <pre className="whitespace-pre-wrap">{JSON.stringify(plan, null, 2)}</pre>
          </div>
        </div>
      ) : null}
    </GlassCard>
  );
}

