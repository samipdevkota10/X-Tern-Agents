"use client";

import * as React from "react";
import useSWR from "swr";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip as ReTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, ArrowRight, DollarSign, ShieldCheck, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";

import { useRequireAuth } from "@/lib/auth";
import { getDashboard } from "@/lib/api";
import type { DashboardResponse, Scenario } from "@/lib/types";
import { useDisruptions } from "@/hooks/useDisruptions";
import { usePendingScenarios } from "@/hooks/useScenarios";
import { GlassCard } from "@/components/shared/GlassCard";
import { KpiCardSkeleton, TableSkeleton } from "@/components/shared/Skeletons";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { Button } from "@/components/ui/button";

function bucketSlaRiskByHour(scenarios: Scenario[]) {
  const map = new Map<string, { sum: number; count: number }>();
  for (const s of scenarios) {
    const d = new Date(s.created_at);
    const key = `${d.getHours().toString().padStart(2, "0")}:00`;
    const prev = map.get(key) ?? { sum: 0, count: 0 };
    map.set(key, { sum: prev.sum + (s.score_json?.sla_risk ?? 0), count: prev.count + 1 });
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([hour, v]) => ({ hour, avg: v.count ? v.sum / v.count : 0 }));
}

function computeRecommendedCost(scenarios: Scenario[]) {
  // recommended = lowest overall_score per order_id
  const bestByOrder = new Map<string, Scenario>();
  for (const s of scenarios) {
    const key = s.order_id || s.scenario_id;
    const prev = bestByOrder.get(key);
    if (!prev || (s.score_json?.overall_score ?? 1e9) < (prev.score_json?.overall_score ?? 1e9)) {
      bestByOrder.set(key, s);
    }
  }
  let sum = 0;
  for (const s of bestByOrder.values()) sum += s.score_json?.cost_impact_usd ?? 0;
  return sum;
}

export default function DashboardPage() {
  useRequireAuth();
  const router = useRouter();

  const dash = useSWR<DashboardResponse>("dashboard", getDashboard, { refreshInterval: 15000 });
  const disruptions = useDisruptions({ status: "open" });
  const pending = usePendingScenarios();

  const pendingScenarios = pending.scenarios as Scenario[];
  const slaSeries = React.useMemo(() => bucketSlaRiskByHour(pendingScenarios), [pendingScenarios]);

  const ordersAtRisk = React.useMemo(() => new Set(pendingScenarios.map((s) => s.order_id)).size, [pendingScenarios]);
  const approvalsCount =
    dash.data?.approval_queue_count ??
    pendingScenarios.filter((s) => s.status === "pending" && s.score_json?.needs_approval).length;
  const activeDisruptions = dash.data?.active_disruptions_count ?? disruptions.disruptions.length;

  const estCostAvoided = React.useMemo(() => {
    // Prefer dashboard if present; fallback to computed recommended sum.
    return dash.data?.estimated_cost_impact_pending ?? computeRecommendedCost(pendingScenarios);
  }, [dash.data?.estimated_cost_impact_pending, pendingScenarios]);

  const recentDisruptions = disruptions.disruptions.slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dash.isLoading ? (
          <>
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </>
        ) : (
          <>
            <GlassCard glow={activeDisruptions > 0} className="p-4 transition-all duration-200">
              <div className="flex items-center justify-between">
                <div className="text-xs text-white/60">Active Disruptions</div>
                <AlertTriangle className="h-4 w-4 text-rose-300" />
              </div>
              <div className="mt-2 text-2xl font-semibold text-white">{activeDisruptions}</div>
              <div className="mt-1 text-[11px] text-white/50">Open disruptions across DCs.</div>
            </GlassCard>

            <GlassCard className="p-4 transition-all duration-200">
              <div className="flex items-center justify-between">
                <div className="text-xs text-white/60">Orders at Risk</div>
                <TriangleAlert className="h-4 w-4 text-amber-300" />
              </div>
              <div className="mt-2 text-2xl font-semibold text-white">{ordersAtRisk}</div>
              <div className="mt-1 text-[11px] text-white/50">Distinct orders in pending scenarios.</div>
            </GlassCard>

            <GlassCard className="p-4 transition-all duration-200">
              <div className="flex items-center justify-between">
                <div className="text-xs text-white/60">Est. Cost Avoided</div>
                <DollarSign className="h-4 w-4 text-emerald-300" />
              </div>
              <div className="mt-2 text-2xl font-semibold text-emerald-200">${Math.round(estCostAvoided)}</div>
              <div className="mt-1 text-[11px] text-white/50">If recommended scenarios are approved.</div>
            </GlassCard>

            <GlassCard className="p-4 transition-all duration-200">
              <div className="flex items-center justify-between">
                <div className="text-xs text-white/60">Pending Approvals</div>
                <ShieldCheck className="h-4 w-4 text-cyan-200" />
              </div>
              <div className="mt-2 text-2xl font-semibold text-cyan-200">{approvalsCount}</div>
              <div className="mt-1 text-[11px] text-white/50">Scenarios requiring manager sign-off.</div>
            </GlassCard>
          </>
        )}
      </div>

      <GlassCard className="p-4">
        <div className="mb-3">
          <div className="text-sm font-semibold text-white">SLA Risk</div>
          <div className="text-[11px] text-white/50">Hourly average risk for pending scenarios.</div>
        </div>
        <div className="h-56">
          {pending.isLoading ? (
            <div className="h-full rounded-2xl glass-skeleton" />
          ) : slaSeries.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-white/40">
              No pending scenarios to chart.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={slaSeries}>
                <defs>
                  <linearGradient id="slaFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
                  axisLine={{ stroke: "rgba(255,255,255,0.12)" }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 1]}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  tick={{ fill: "rgba(255,255,255,0.6)", fontSize: 11 }}
                  axisLine={{ stroke: "rgba(255,255,255,0.12)" }}
                  tickLine={false}
                />
                <ReTooltip
                  contentStyle={{
                    background: "rgba(0,0,0,0.55)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 16,
                    backdropFilter: "blur(12px)",
                    color: "white",
                    fontSize: 12,
                  }}
                  formatter={(val) => `${(Number(val) * 100).toFixed(1)}%`}
                />
                <Area
                  type="monotone"
                  dataKey="avg"
                  stroke="#22d3ee"
                  fill="url(#slaFill)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </GlassCard>

      <GlassCard className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-white">Recent Disruptions</div>
            <div className="text-[11px] text-white/50">Last 5 disruptions (from API).</div>
          </div>
          <Button
            variant="ghost"
            className="text-cyan-200 hover:bg-white/10 hover:text-cyan-100 transition-all duration-200"
            onClick={() => router.push("/disruptions")}
          >
            View all <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </div>

        {disruptions.isLoading ? (
          <TableSkeleton rows={5} />
        ) : (
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-white/40">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2 text-left font-medium">Severity</th>
                  <th className="px-2 py-2 text-left font-medium">Type</th>
                  <th className="px-2 py-2 text-left font-medium">Affected Orders</th>
                  <th className="px-2 py-2 text-left font-medium">Status</th>
                  <th className="px-2 py-2 text-right font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {recentDisruptions.map((d) => {
                  const orderSet = new Set(
                    pendingScenarios.filter((s) => s.disruption_id === d.id).map((s) => s.order_id),
                  );
                  return (
                    <tr key={d.id} className="border-b border-white/5 hover:bg-white/5 transition-all duration-200">
                      <td className="px-2 py-2">
                        <SeverityBadge severity={d.severity} />
                      </td>
                      <td className="px-2 py-2 text-white/80">{d.type}</td>
                      <td className="px-2 py-2 text-white/80">{orderSet.size || "—"}</td>
                      <td className="px-2 py-2 text-white/60">{d.status}</td>
                      <td className="px-2 py-2 text-right text-white/50">
                        {new Date(d.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
                {recentDisruptions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-xs text-white/40">
                      No disruptions found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

