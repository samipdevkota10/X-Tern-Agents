"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { toast } from "sonner";

import { useRequireAuth, useAuth } from "@/lib/auth";
import type { Scenario, ScenarioScore, Disruption } from "@/lib/types";
import { approveScenario, rejectScenario } from "@/lib/api";
import { useScenarios } from "@/hooks/useScenarios";
import { useDisruptions } from "@/hooks/useDisruptions";

import { GlassCard } from "@/components/shared/GlassCard";
import { ScenarioCard } from "@/components/shared/ScenarioCard";
import { CardGridSkeleton } from "@/components/shared/Skeletons";
import { cn } from "@/lib/utils";

type StatusTab = "pending" | "approved" | "rejected" | "all";

type Group = {
  disruption_id: string;
  disruption_type?: string;
  scenarios: Scenario[];
};

function groupByDisruption(items: Scenario[], disruptionMap: Map<string, Disruption>): Group[] {
  const map = new Map<string, Scenario[]>();
  for (const s of items) {
    if (!map.has(s.disruption_id)) map.set(s.disruption_id, []);
    map.get(s.disruption_id)!.push(s);
  }
  return Array.from(map.entries()).map(([disruption_id, scenarios]) => ({
    disruption_id,
    disruption_type: disruptionMap.get(disruption_id)?.type,
    scenarios: scenarios.sort((a, b) => (a.created_at > b.created_at ? -1 : 1)),
  }));
}

function computeRecommendedScenarioIds(items: Scenario[]): Set<string> {
  const bestByKey = new Map<string, Scenario>();
  for (const s of items) {
    const key = s.order_id || s.scenario_id;
    const prev = bestByKey.get(key);
    const score = (s.score_json as ScenarioScore)?.overall_score ?? 1e9;
    const prevScore = prev ? ((prev.score_json as ScenarioScore)?.overall_score ?? 1e9) : 1e9;
    if (!prev || score < prevScore) bestByKey.set(key, s);
  }
  return new Set(Array.from(bestByKey.values()).map((s) => s.scenario_id));
}

export default function ScenariosPage() {
  useRequireAuth();
  const { isManager } = useAuth();

  // Analysts default to Approved; managers default to Pending
  const [statusTab, setStatusTab] = React.useState<StatusTab>(isManager ? "pending" : "approved");

  const { scenarios, isLoading, mutate } = useScenarios({
    status: statusTab === "all" ? undefined : statusTab,
  });
  const { disruptions } = useDisruptions();

  // Create a map for quick lookup of disruption by ID
  const disruptionMap = React.useMemo(() => {
    const map = new Map<string, Disruption>();
    for (const d of disruptions) {
      map.set(d.id, d);
    }
    return map;
  }, [disruptions]);

  const groups = React.useMemo(() => groupByDisruption(scenarios, disruptionMap), [scenarios, disruptionMap]);
  const recommendedIds = React.useMemo(() => computeRecommendedScenarioIds(scenarios), [scenarios]);

  const onApprove = async (id: string, note: string) => {
    try {
      await approveScenario(id, { note });
      toast.success("Scenario approved");
      mutate();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to approve");
    }
  };

  const onReject = async (id: string, note: string) => {
    try {
      await rejectScenario(id, { note });
      toast.success("Scenario rejected");
      mutate();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to reject");
    }
  };

  const tabs: { key: StatusTab; label: string }[] = [
    { key: "pending", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "rejected", label: "Rejected" },
    { key: "all", label: "All" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">Scenario Comparison</div>
          <div className="text-[11px] text-white/50">
            Grouped by disruption. Recommended plan is the lowest overall_score per order.
          </div>
        </div>
        <div className="flex rounded-full border border-white/10 bg-black/20 p-1">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setStatusTab(t.key)}
              className={cn(
                "rounded-full px-3 py-1.5 text-[11px] font-medium transition-all duration-200",
                statusTab === t.key
                  ? "bg-cyan-400/20 text-cyan-200 shadow-[0_0_12px_rgba(34,211,238,0.25)]"
                  : "text-white/60 hover:bg-white/10 hover:text-white",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <CardGridSkeleton count={6} />
      ) : groups.length === 0 ? (
        <div className="glass-card p-8 text-center text-xs text-white/50">
          {statusTab === "all"
            ? "No scenarios available. Run the planner first."
            : `No ${statusTab} scenarios. Try another tab or run the planner first.`}
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((g) => (
            <DisruptionGroup
              key={g.disruption_id}
              group={g}
              isManager={isManager}
              recommendedIds={recommendedIds}
              onApprove={onApprove}
              onReject={onReject}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DisruptionGroup(props: {
  group: Group;
  isManager: boolean;
  recommendedIds: Set<string>;
  onApprove: (scenarioId: string, note: string) => Promise<void>;
  onReject: (scenarioId: string, note: string) => Promise<void>;
}) {
  const [open, setOpen] = React.useState(true);
  const { group } = props;

  // Create friendly label from disruption type
  const typeLabel = group.disruption_type
    ? group.disruption_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Unknown";

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left"
      >
        <GlassCard className="px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-all duration-200">
          <div className="min-w-0">
            <div className="text-xs font-semibold text-white">
              {typeLabel} <span className="font-mono text-white/50 text-[10px]">({group.disruption_id.slice(0, 8)}…)</span>
            </div>
            <div className="text-[11px] text-white/50">{group.scenarios.length} scenarios</div>
          </div>
          <ChevronDown className={`h-4 w-4 text-white/50 transition-all duration-200 ${open ? "rotate-180" : ""}`} />
        </GlassCard>
      </button>

      {open ? (
        <div className="grid gap-4 md:grid-cols-2">
          {group.scenarios.map((s) => (
            <ScenarioCard
              key={s.scenario_id}
              scenario={s}
              recommended={props.recommendedIds.has(s.scenario_id)}
              isManager={props.isManager}
              onApprove={(note) => props.onApprove(s.scenario_id, note)}
              onReject={(note) => props.onReject(s.scenario_id, note)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

