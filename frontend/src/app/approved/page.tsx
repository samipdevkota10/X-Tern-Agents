"use client";

import * as React from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { useRequireAuth } from "@/lib/auth";
import type { Scenario, Disruption } from "@/lib/types";
import { listScenarios } from "@/lib/api";
import { useDisruptions } from "@/hooks/useDisruptions";
import useSWR from "swr";

import { GlassCard } from "@/components/shared/GlassCard";
import { ActionTypeBadge } from "@/components/shared/ActionTypeBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { TableSkeleton } from "@/components/shared/Skeletons";
import { Button } from "@/components/ui/button";

function useApprovedScenarios() {
  const { data, error, isLoading, mutate } = useSWR<Scenario[]>(
    ["scenarios-approved"],
    () => listScenarios({ status: "approved", limit: 50 }),
    { refreshInterval: 15000 },
  );
  return { scenarios: data ?? [], isLoading, error, mutate };
}

function groupByDisruption(
  scenarios: Scenario[],
  disruptionMap: Map<string, Disruption>,
): { disruption_id: string; disruption_type?: string; scenarios: Scenario[] }[] {
  const map = new Map<string, Scenario[]>();
  for (const s of scenarios) {
    if (!map.has(s.disruption_id)) map.set(s.disruption_id, []);
    map.get(s.disruption_id)!.push(s);
  }
  return Array.from(map.entries()).map(([disruption_id, scenarios]) => ({
    disruption_id,
    disruption_type: disruptionMap.get(disruption_id)?.type,
    scenarios: scenarios.sort((a, b) => (a.created_at > b.created_at ? -1 : 1)),
  }));
}

export default function ApprovedActionsPage() {
  useRequireAuth();
  const router = useRouter();

  const { scenarios, isLoading, mutate } = useApprovedScenarios();
  const { disruptions } = useDisruptions();

  const disruptionMap = React.useMemo(() => {
    const map = new Map<string, Disruption>();
    for (const d of disruptions) {
      map.set(d.id, d);
    }
    return map;
  }, [disruptions]);

  const groups = React.useMemo(
    () => groupByDisruption(scenarios, disruptionMap),
    [scenarios, disruptionMap],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            Approved Actions
          </div>
          <div className="text-[11px] text-white/50">
            Manager-approved scenarios now in effect. See what decisions have been applied.
          </div>
        </div>
        <Button
          variant="ghost"
          className="text-cyan-200 hover:bg-white/10 hover:text-cyan-100 transition-all duration-200"
          onClick={() => router.push("/scenarios")}
        >
          All Scenarios <ArrowRight className="ml-1 h-4 w-4" />
        </Button>
      </div>

      {isLoading ? (
        <TableSkeleton rows={10} />
      ) : groups.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No approved actions yet"
          description="When a manager approves scenarios, they will appear here. Run the planner and approve scenarios to see them."
          actionLabel="Go to Scenarios"
          onAction={() => router.push("/scenarios")}
        />
      ) : (
        <div className="space-y-4">
          {groups.map((g) => (
            <GlassCard key={g.disruption_id} className="p-4">
              <div className="mb-3">
                <div className="text-xs font-semibold text-white">
                  {g.disruption_type
                    ? g.disruption_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                    : "Unknown"}{" "}
                  <span className="font-mono text-white/50 text-[10px]">
                    ({g.disruption_id.slice(0, 8)}…)
                  </span>
                </div>
                <div className="text-[11px] text-white/50">
                  {g.scenarios.length} approved action{g.scenarios.length !== 1 ? "s" : ""}
                </div>
              </div>
              <div className="max-h-72 overflow-auto">
                <table className="w-full text-xs">
                  <thead className="text-[11px] uppercase tracking-wide text-white/40">
                    <tr className="border-b border-white/10">
                      <th className="px-2 py-2 text-left font-medium">Order</th>
                      <th className="px-2 py-2 text-left font-medium">Action</th>
                      <th className="px-2 py-2 text-left font-medium">Cost</th>
                      <th className="px-2 py-2 text-left font-medium">SLA Risk</th>
                      <th className="px-2 py-2 text-right font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.scenarios.map((s) => (
                      <tr
                        key={s.scenario_id}
                        className="border-b border-white/5 hover:bg-white/5 transition-all duration-200"
                      >
                        <td className="px-2 py-2 font-mono text-white/80">{s.order_id}</td>
                        <td className="px-2 py-2">
                          <ActionTypeBadge action={s.action_type} />
                        </td>
                        <td className="px-2 py-2 text-amber-200">
                          ${Math.round(s.score_json?.cost_impact_usd ?? 0)}
                        </td>
                        <td className="px-2 py-2 text-rose-200">
                          {((s.score_json?.sla_risk ?? 0) * 100).toFixed(1)}%
                        </td>
                        <td className="px-2 py-2 text-right text-white/50">
                          {new Date(s.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
