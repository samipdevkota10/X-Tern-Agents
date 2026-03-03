"use client";

import * as React from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";

import { useRequireAuth } from "@/lib/auth";
import { useAuditLogs } from "@/hooks/useAuditLogs";

import { GlassCard } from "@/components/shared/GlassCard";
import { AuditLogRow } from "@/components/shared/AuditLogRow";
import { TableSkeleton } from "@/components/shared/Skeletons";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function AuditPage() {
  useRequireAuth();

  const [agentName, setAgentName] = React.useState<string>("");
  const [decision, setDecision] = React.useState<string>("all");
  const [pipelineRunId, setPipelineRunId] = React.useState<string>("");
  const [disruptionId, setDisruptionId] = React.useState<string>("");
  const [dateFrom, setDateFrom] = React.useState<string>("");
  const [dateTo, setDateTo] = React.useState<string>("");

  const logsQuery = useAuditLogs({
    agent_name: agentName || undefined,
    human_decision: decision === "all" ? undefined : decision,
    pipeline_run_id: pipelineRunId || undefined,
    limit: 250,
    offset: 0,
  });

  const filtered = React.useMemo(() => {
    const items = logsQuery.logs;
    return items.filter((l) => {
      const ts = new Date(l.timestamp).getTime();
      if (dateFrom) {
        const from = new Date(dateFrom).getTime();
        if (ts < from) return false;
      }
      if (dateTo) {
        const to = new Date(dateTo).getTime() + 24 * 60 * 60 * 1000;
        if (ts > to) return false;
      }
      if (disruptionId) {
        const hay = `${l.input_summary}\n${l.output_summary}`;
        if (!hay.includes(disruptionId)) return false;
      }
      return true;
    });
  }, [logsQuery.logs, dateFrom, dateTo, disruptionId]);

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "disruptiq_audit_logs.json";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Exported audit logs");
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm font-semibold text-white">Audit Log</div>
        <div className="text-[11px] text-white/50">Filterable decision trail across agents and humans.</div>
      </div>

      <GlassCard className="p-4 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <div className="text-[11px] text-white/60 mb-1">Agent</div>
            <Input
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="Supervisor, HumanApproval…"
              className="h-9 w-56 bg-black/30 border-white/10 text-white/80 placeholder:text-white/30"
            />
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">Decision</div>
            <Select value={decision} onValueChange={setDecision}>
              <SelectTrigger className="h-9 w-44 border-white/10 bg-black/30 text-white/80">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="edited">Edited</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">Run ID</div>
            <Input
              value={pipelineRunId}
              onChange={(e) => setPipelineRunId(e.target.value)}
              placeholder="pipeline_run_id"
              className="h-9 w-64 bg-black/30 border-white/10 text-white/80 placeholder:text-white/30"
            />
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">Disruption ID</div>
            <Input
              value={disruptionId}
              onChange={(e) => setDisruptionId(e.target.value)}
              placeholder="client-side filter"
              className="h-9 w-56 bg-black/30 border-white/10 text-white/80 placeholder:text-white/30"
            />
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">From</div>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="h-9 w-44 bg-black/30 border-white/10 text-white/80"
            />
          </div>
          <div>
            <div className="text-[11px] text-white/60 mb-1">To</div>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="h-9 w-44 bg-black/30 border-white/10 text-white/80"
            />
          </div>

          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" className="hover:bg-white/10" onClick={() => logsQuery.mutate()}>
              Refresh
            </Button>
            <Button
              onClick={exportJson}
              className="rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200"
            >
              <Download className="mr-1 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/25 overflow-auto max-h-[560px]">
          {logsQuery.isLoading ? (
            <TableSkeleton rows={10} />
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-xs text-white/50">No audit entries match your filters.</div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-black/40 backdrop-blur-xl text-[11px] uppercase tracking-wide text-white/40">
                <tr className="border-b border-white/10">
                  <th className="px-3 py-2 text-left font-medium">Timestamp</th>
                  <th className="px-3 py-2 text-left font-medium">Run ID</th>
                  <th className="px-3 py-2 text-left font-medium">Agent</th>
                  <th className="px-3 py-2 text-left font-medium">Input</th>
                  <th className="px-3 py-2 text-left font-medium">Output</th>
                  <th className="px-3 py-2 text-left font-medium">Confidence</th>
                  <th className="px-3 py-2 text-left font-medium">Decision</th>
                  <th className="px-3 py-2 text-left font-medium">Approver</th>
                  <th className="px-3 py-2 text-left font-medium">Note</th>
                  <th className="px-3 py-2 text-right font-medium" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <AuditLogRow key={e.log_id} entry={e} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </GlassCard>
    </div>
  );
}

