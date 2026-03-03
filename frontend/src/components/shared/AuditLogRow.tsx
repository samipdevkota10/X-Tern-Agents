"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, Copy } from "lucide-react";
import { toast } from "sonner";

import type { DecisionLogEntry } from "@/lib/types";
import { cn } from "@/lib/utils";
import { DecisionBadge } from "@/components/shared/DecisionBadge";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { Button } from "@/components/ui/button";

export function AuditLogRow(props: { entry: DecisionLogEntry }) {
  const { entry } = props;
  const [open, setOpen] = React.useState(false);

  const copyRunId = async () => {
    try {
      await navigator.clipboard.writeText(entry.pipeline_run_id);
      toast.success("Run ID copied");
    } catch {
      toast.error("Failed to copy");
    }
  };

  const runIdShort =
    entry.pipeline_run_id.length > 12
      ? `${entry.pipeline_run_id.slice(0, 12)}…`
      : entry.pipeline_run_id;

  const pretty = (s: string) => {
    try {
      const obj = JSON.parse(s);
      return JSON.stringify(obj, null, 2);
    } catch {
      return s;
    }
  };

  return (
    <>
      <tr className="border-b border-white/5 hover:bg-white/5 transition-all duration-200">
        <td className="px-3 py-2 align-top text-[11px] text-white/60">
          {new Date(entry.timestamp).toLocaleString()}
        </td>
        <td className="px-3 py-2 align-top text-xs text-white/80">
          <div className="flex items-center gap-2">
            <span className="font-mono">{runIdShort}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-white/60 hover:text-cyan-200 hover:bg-white/10"
              onClick={copyRunId}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </div>
        </td>
        <td className="px-3 py-2 align-top text-xs text-white/80">{entry.agent_name}</td>
        <td className="px-3 py-2 align-top text-xs text-white/60 max-w-[260px] truncate">
          {entry.input_summary}
        </td>
        <td className="px-3 py-2 align-top text-xs text-white/60 max-w-[260px] truncate">
          {entry.output_summary}
        </td>
        <td className="px-3 py-2 align-top w-[220px]">
          <ConfidenceBar score={entry.confidence_score} />
        </td>
        <td className="px-3 py-2 align-top">
          <DecisionBadge decision={entry.human_decision} />
        </td>
        <td className="px-3 py-2 align-top text-xs text-white/60">{entry.approver_id ?? "—"}</td>
        <td className="px-3 py-2 align-top text-xs text-white/60">{entry.approver_note ?? "—"}</td>
        <td className="px-3 py-2 align-top text-right">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-white/60 hover:text-cyan-200 hover:bg-white/10"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </td>
      </tr>
      {open ? (
        <tr className="border-b border-white/5 bg-black/30">
          <td colSpan={10} className="px-3 py-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-wide text-white/40">Input summary</div>
                <div className={cn("code-block max-h-64 overflow-auto")}>
                  <pre className="whitespace-pre-wrap">{pretty(entry.input_summary)}</pre>
                </div>
              </div>
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-wide text-white/40">Output summary</div>
                <div className={cn("code-block max-h-64 overflow-auto")}>
                  <pre className="whitespace-pre-wrap">{pretty(entry.output_summary)}</pre>
                </div>
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

