"use client";

import * as React from "react";
import { CheckCircle2, Inbox, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useRequireAuth, useAuth } from "@/lib/auth";
import type { Scenario } from "@/lib/types";
import { approveScenario, rejectScenario } from "@/lib/api";
import { usePendingScenarios } from "@/hooks/useScenarios";

import { GlassCard } from "@/components/shared/GlassCard";
import { ActionTypeBadge } from "@/components/shared/ActionTypeBadge";
import { MetricPill } from "@/components/shared/MetricPill";
import { EmptyState } from "@/components/shared/EmptyState";
import { TableSkeleton } from "@/components/shared/Skeletons";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export default function ApprovalsPage() {
  useRequireAuth();
  const router = useRouter();
  const auth = useAuth();

  React.useEffect(() => {
    if (!auth.loading && !auth.isManager) {
      toast.error("Access restricted to managers.");
      router.replace("/dashboard");
    }
  }, [auth.loading, auth.isManager, router]);

  const pending = usePendingScenarios();
  const scenarios = (pending.scenarios as Scenario[]).filter(
    (s) => s.status === "pending" && s.score_json?.needs_approval,
  );

  const [notes, setNotes] = React.useState<Record<string, string>>({});
  const [bulkOpen, setBulkOpen] = React.useState(false);
  const [bulkBusy, setBulkBusy] = React.useState(false);

  const approve = async (id: string) => {
    const note = notes[id] || "Approved in DisruptIQ";
    try {
      await approveScenario(id, { note });
      toast.success("Approved");
      pending.mutate();
    } catch (e: unknown) {
      toast.error(getErrMsg(e, "Approve failed"));
    }
  };

  const reject = async (id: string) => {
    const note = notes[id] || "Rejected in DisruptIQ";
    try {
      await rejectScenario(id, { note });
      toast.success("Rejected");
      pending.mutate();
    } catch (e: unknown) {
      toast.error(getErrMsg(e, "Reject failed"));
    }
  };

  const bulkApprove = async () => {
    setBulkBusy(true);
    try {
      for (let i = 0; i < scenarios.length; i++) {
        const s = scenarios[i];
        toast.message(`Bulk approving ${i + 1}/${scenarios.length}`, {
          description: s.scenario_id,
        });
        try {
          await approveScenario(s.scenario_id, { note: notes[s.scenario_id] || "Bulk approved in DisruptIQ" });
        } catch (e: unknown) {
          toast.error(`Failed to approve ${s.scenario_id}`, { description: getErrMsg(e, "Unknown error") });
        }
      }
      toast.success("Bulk approval completed");
      pending.mutate();
    } finally {
      setBulkBusy(false);
      setBulkOpen(false);
    }
  };

  if (!auth.isManager) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">Approval Queue</div>
          <div className="text-[11px] text-white/50">Manager-only: approve scenarios requiring gating.</div>
        </div>
        <Button
          onClick={() => setBulkOpen(true)}
          disabled={scenarios.length === 0}
          className="rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all duration-200"
        >
          <CheckCircle2 className="mr-1 h-4 w-4" />
          Bulk approve ({scenarios.length})
        </Button>
      </div>

      <GlassCard className="p-4">
        {pending.isLoading ? (
          <TableSkeleton rows={8} />
        ) : scenarios.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="All caught up"
            description="No scenarios currently require approval."
            actionLabel="Go to Dashboard"
            onAction={() => router.push("/dashboard")}
          />
        ) : (
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-white/40">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2 text-left font-medium">Scenario</th>
                  <th className="px-2 py-2 text-left font-medium">Disruption</th>
                  <th className="px-2 py-2 text-left font-medium">Action</th>
                  <th className="px-2 py-2 text-left font-medium">Metrics</th>
                  <th className="px-2 py-2 text-left font-medium">Note</th>
                  <th className="px-2 py-2 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s) => (
                  <tr key={s.scenario_id} className="border-b border-white/5 hover:bg-white/5 transition-all duration-200">
                    <td className="px-2 py-2 align-top">
                      <div className="font-mono text-white/80">{s.scenario_id.slice(0, 10)}…</div>
                      <div className="text-[11px] text-white/50">Order {s.order_id}</div>
                    </td>
                    <td className="px-2 py-2 align-top text-white/60 font-mono">{s.disruption_id.slice(0, 10)}…</td>
                    <td className="px-2 py-2 align-top">
                      <ActionTypeBadge action={s.action_type} />
                    </td>
                    <td className="px-2 py-2 align-top space-x-2">
                      <MetricPill label="Cost" value={`$${Math.round(s.score_json.cost_impact_usd)}`} color="amber" />
                      <MetricPill label="SLA" value={`${(s.score_json.sla_risk * 100).toFixed(1)}%`} color="rose" />
                    </td>
                    <td className="px-2 py-2 align-top">
                      <Input
                        value={notes[s.scenario_id] ?? ""}
                        onChange={(e) => setNotes((p) => ({ ...p, [s.scenario_id]: e.target.value }))}
                        placeholder="Short note…"
                        className="h-9 bg-black/30 border-white/10 text-white/80 placeholder:text-white/30"
                      />
                    </td>
                    <td className="px-2 py-2 align-top text-right space-x-2">
                      <Button
                        size="sm"
                        onClick={() => approve(s.scenario_id)}
                        className="rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all duration-200"
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => reject(s.scenario_id)}
                        className="rounded-full transition-all duration-200"
                      >
                        Reject
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
        <DialogContent className="border-white/10 bg-black/50 backdrop-blur-2xl text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-300" />
              Bulk Approve
            </DialogTitle>
          </DialogHeader>
          <div className="text-xs text-white/60">
            Approve all visible scenarios sequentially. Constraint failures will be reported per item.
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setBulkOpen(false)} className="hover:bg-white/10" disabled={bulkBusy}>
              Cancel
            </Button>
            <Button
              onClick={bulkApprove}
              disabled={bulkBusy}
              className="rounded-full bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              {bulkBusy ? "Approving…" : "Approve all"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function getErrMsg(e: unknown, fallback: string) {
  return e instanceof Error ? e.message : fallback;
}

