"use client";

import * as React from "react";
import { AlertTriangle, Eye, Plus } from "lucide-react";

import { useRequireAuth } from "@/lib/auth";
import type { Disruption, DisruptionCreateRequest, DisruptionType, Scenario } from "@/lib/types";
import { createDisruption } from "@/lib/api";
import { useDisruptions } from "@/hooks/useDisruptions";
import { usePendingScenarios } from "@/hooks/useScenarios";
import { toast } from "sonner";

import { GlassCard } from "@/components/shared/GlassCard";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { TableSkeleton } from "@/components/shared/Skeletons";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";

export default function DisruptionsPage() {
  useRequireAuth();

  const [status, setStatus] = React.useState<string>("open");
  const [type, setType] = React.useState<string>("all");
  const [severity, setSeverity] = React.useState<string>("all");
  const [selected, setSelected] = React.useState<Disruption | null>(null);

  const disruptions = useDisruptions({
    status: status === "all" ? undefined : status,
    type: type === "all" ? undefined : type,
    severity: severity === "all" ? undefined : Number(severity),
  });

  const pending = usePendingScenarios();
  const pendingScenarios = pending.scenarios as Scenario[];

  const affectedOrderIds = (disruptionId: string) => {
    const set = new Set<string>();
    for (const s of pendingScenarios) {
      if (s.disruption_id === disruptionId) set.add(s.order_id);
    }
    return Array.from(set);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-white">Disruptions Inbox</div>
          <div className="text-[11px] text-white/50">Filter and inspect incoming disruption signals.</div>
        </div>

        <CreateDisruptionButton onCreated={() => disruptions.mutate()} />
      </div>

      <GlassCard className="p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <Select value={type} onValueChange={setType}>
            <SelectTrigger className="h-9 w-44 border-white/10 bg-black/30 text-white/80">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="late_truck">Late truck</SelectItem>
              <SelectItem value="stockout">Stockout</SelectItem>
              <SelectItem value="machine_down">Machine down</SelectItem>
            </SelectContent>
          </Select>

          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="h-9 w-40 border-white/10 bg-black/30 text-white/80">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {["1", "2", "3", "4", "5"].map((s) => (
                <SelectItem key={s} value={s}>
                  Severity {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="h-9 w-40 border-white/10 bg-black/30 text-white/80">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {disruptions.isLoading ? (
          <TableSkeleton rows={8} />
        ) : disruptions.disruptions.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title="No disruptions found"
            description="Try adjusting filters or create a test disruption to validate the end-to-end flow."
          />
        ) : (
          <div className="max-h-[560px] overflow-auto">
            <table className="w-full text-xs">
              <thead className="text-[11px] uppercase tracking-wide text-white/40">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2 text-left font-medium">Severity</th>
                  <th className="px-2 py-2 text-left font-medium">Type</th>
                  <th className="px-2 py-2 text-left font-medium">Description</th>
                  <th className="px-2 py-2 text-left font-medium">Affected Orders</th>
                  <th className="px-2 py-2 text-left font-medium">Timestamp</th>
                  <th className="px-2 py-2 text-left font-medium">Status</th>
                  <th className="px-2 py-2 text-right font-medium">View</th>
                </tr>
              </thead>
              <tbody>
                {disruptions.disruptions.map((d) => {
                  const affected = affectedOrderIds(d.id);
                  const details = d.details_json as Record<string, unknown>;
                  const sku = typeof details.sku === "string" ? details.sku : "—";
                  const truckId = typeof details.truck_id === "string" ? details.truck_id : "—";
                  const process = typeof details.process === "string" ? details.process : "—";
                  const shortDesc =
                    d.type === "stockout"
                      ? `SKU ${sku} shortage`
                      : d.type === "late_truck"
                        ? `Truck ${truckId} delayed`
                        : d.type === "machine_down"
                          ? `Process ${process} impacted`
                          : "Disruption signal";
                  return (
                    <tr
                      key={d.id}
                      className="border-b border-white/5 hover:bg-white/5 transition-all duration-200"
                    >
                      <td className="px-2 py-2">
                        <SeverityBadge severity={d.severity} />
                      </td>
                      <td className="px-2 py-2 text-white/80">{d.type}</td>
                      <td className="px-2 py-2 text-white/60">{shortDesc}</td>
                      <td className="px-2 py-2 text-white/80">{affected.length || "—"}</td>
                      <td className="px-2 py-2 text-white/60">
                        {new Date(d.timestamp).toLocaleString()}
                      </td>
                      <td className="px-2 py-2 text-white/60">{d.status}</td>
                      <td className="px-2 py-2 text-right">
                        <Button
                          variant="ghost"
                          className="h-8 px-3 text-cyan-200 hover:bg-white/10 transition-all duration-200"
                          onClick={() => setSelected(d)}
                        >
                          <Eye className="mr-1 h-4 w-4" />
                          View
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>

      <Sheet open={!!selected} onOpenChange={(o) => (!o ? setSelected(null) : null)}>
        <SheetContent className="border-white/10 bg-black/50 backdrop-blur-2xl text-white">
          {selected ? (
            <>
              <SheetHeader>
                <SheetTitle className="text-white flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-300" />
                  Disruption Details
                </SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-4 text-xs">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={selected.severity} />
                  <span className="text-white/80">{selected.type}</span>
                  <span className="text-white/40 font-mono">{selected.id.slice(0, 10)}…</span>
                </div>
                <div className="text-[11px] text-white/50">
                  {new Date(selected.timestamp).toLocaleString()} • {selected.status}
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-white/40 mb-1">details_json</div>
                  <div className="code-block max-h-64 overflow-auto">
                    <pre className="whitespace-pre-wrap">{JSON.stringify(selected.details_json, null, 2)}</pre>
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-white/40 mb-1">Affected orders</div>
                  <div className="glass-card p-3">
                    {affectedOrderIds(selected.id).length === 0 ? (
                      <div className="text-[11px] text-white/50">
                        Affected orders computed from scenarios. None available yet.
                      </div>
                    ) : (
                      <ul className="space-y-1">
                        {affectedOrderIds(selected.id).map((oid) => (
                          <li key={oid} className="font-mono text-[11px] text-white/80">
                            {oid}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function CreateDisruptionButton(props: { onCreated: () => void }) {
  const [open, setOpen] = React.useState(false);
  const [type, setType] = React.useState<DisruptionType>("late_truck");
  const [severity, setSeverity] = React.useState("3");
  const [details, setDetails] = React.useState<string>(JSON.stringify({ note: "Test disruption created from DisruptIQ UI" }, null, 2));
  const [submitting, setSubmitting] = React.useState(false);

  const submit = async () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(details);
    } catch {
      toast.error("details_json must be valid JSON");
      return;
    }

    const body: DisruptionCreateRequest = {
      type,
      severity: Number(severity),
      details_json: parsed,
    };

    setSubmitting(true);
    try {
      await createDisruption(body);
      toast.success("Disruption created");
      props.onCreated();
      setOpen(false);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to create disruption";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200">
          <Plus className="mr-1 h-4 w-4" />
          Create Test Disruption
        </Button>
      </DialogTrigger>
      <DialogContent className="border-white/10 bg-black/50 backdrop-blur-2xl text-white">
        <DialogHeader>
          <DialogTitle className="text-white flex items-center gap-2">
            <Plus className="h-4 w-4 text-cyan-200" />
            Create Test Disruption
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 text-xs">
          <div className="grid gap-3 grid-cols-2">
            <div>
              <div className="text-[11px] text-white/60 mb-1">Type</div>
              <Select value={type} onValueChange={(v) => setType(v as DisruptionType)}>
                <SelectTrigger className="h-9 border-white/10 bg-black/30 text-white/80">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="late_truck">Late truck</SelectItem>
                  <SelectItem value="stockout">Stockout</SelectItem>
                  <SelectItem value="machine_down">Machine down</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <div className="text-[11px] text-white/60 mb-1">Severity</div>
              <Select value={severity} onValueChange={setSeverity}>
                <SelectTrigger className="h-9 border-white/10 bg-black/30 text-white/80">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["1", "2", "3", "4", "5"].map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">details_json</div>
            <Textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              className="min-h-[140px] border-white/10 bg-black/30 text-white/80 placeholder:text-white/30"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)} className="hover:bg-white/10">
            Cancel
          </Button>
          <Button onClick={submit} disabled={submitting} className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300">
            {submitting ? "Creating…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

