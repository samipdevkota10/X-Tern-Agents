"use client";

import { cn } from "@/lib/utils";
import type { DecisionLogEntry } from "@/lib/types";
import { RoutingDecisionBadge } from "./RoutingDecisionBadge";

const AGENT_COLORS: Record<string, string> = {
  "Signal Intake": "border-blue-500/40 bg-blue-500/15 text-blue-200",
  "signal_intake": "border-blue-500/40 bg-blue-500/15 text-blue-200",
  "Constraint Builder": "border-amber-500/40 bg-amber-500/15 text-amber-200",
  "constraint_builder": "border-amber-500/40 bg-amber-500/15 text-amber-200",
  "Scenario Generator": "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
  "scenario_generator": "border-emerald-500/40 bg-emerald-500/15 text-emerald-200",
  "Tradeoff Scoring": "border-purple-500/40 bg-purple-500/15 text-purple-200",
  "tradeoff_scoring": "border-purple-500/40 bg-purple-500/15 text-purple-200",
  "Router": "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
  "router": "border-cyan-500/40 bg-cyan-500/15 text-cyan-200",
  "Supervisor": "border-pink-500/40 bg-pink-500/15 text-pink-200",
  "supervisor": "border-pink-500/40 bg-pink-500/15 text-pink-200",
  "Finalizer": "border-teal-500/40 bg-teal-500/15 text-teal-200",
  "finalizer": "border-teal-500/40 bg-teal-500/15 text-teal-200",
};

const AGENT_ICONS: Record<string, string> = {
  "Signal Intake": "📡",
  "signal_intake": "📡",
  "Constraint Builder": "📊",
  "constraint_builder": "📊",
  "Scenario Generator": "💡",
  "scenario_generator": "💡",
  "Tradeoff Scoring": "⚖️",
  "tradeoff_scoring": "⚖️",
  "Router": "🔀",
  "router": "🔀",
  "Supervisor": "🎯",
  "supervisor": "🎯",
  "Finalizer": "✅",
  "finalizer": "✅",
};

function formatAgentName(name: string): string {
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

interface RoutingTraceEntry {
  ts: string;
  from: string;
  llm_next: string | null;
  final: string;
  override: string | null;
  confidence: number | null;
  reason: string | null;
}

interface AgentActivityLogProps {
  logs: DecisionLogEntry[];
  routingTrace?: RoutingTraceEntry[];
  isRunning?: boolean;
  className?: string;
  expanded?: boolean;
}

export function AgentActivityLog({
  logs,
  routingTrace = [],
  isRunning = false,
  className,
  expanded = false,
}: AgentActivityLogProps) {
  // Combine and sort by timestamp
  const sortedLogs = [...logs].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  if (sortedLogs.length === 0 && routingTrace.length === 0) {
    return (
      <div className={cn("glass-card p-4", className)}>
        <div className="text-xs text-white/50 text-center py-4">
          {isRunning ? "Waiting for agent activity..." : "No agent activity recorded"}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("glass-card p-4", className)}>
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs font-semibold text-white flex items-center gap-2">
          <span>Agent Activity Log</span>
          {isRunning && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 text-[10px]">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
              Live
            </span>
          )}
        </div>
        <div className="text-[11px] text-white/50">
          {sortedLogs.length} actions
        </div>
      </div>

      <div className={cn(
        "space-y-2 overflow-y-auto",
        expanded ? "max-h-[400px]" : "max-h-[200px]"
      )}>
        {sortedLogs.map((log, idx) => {
          const agentColor = AGENT_COLORS[log.agent_name] ?? "border-white/20 bg-white/5 text-white/80";
          const agentIcon = AGENT_ICONS[log.agent_name] ?? "🤖";
          
          // Find matching routing trace entry
          const routingEntry = routingTrace.find(
            (r) => r.from === log.agent_name.toLowerCase().replace(" ", "_")
          );

          return (
            <div
              key={log.log_id || idx}
              className={cn(
                "rounded-lg border p-3 transition-all duration-200",
                agentColor
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{agentIcon}</span>
                  <span className="text-xs font-semibold">
                    {formatAgentName(log.agent_name)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-white/50">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  {log.confidence_score !== undefined && log.confidence_score !== null && (
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full",
                        log.confidence_score >= 0.8
                          ? "bg-emerald-500/20 text-emerald-300"
                          : log.confidence_score >= 0.5
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-rose-500/20 text-rose-300"
                      )}
                    >
                      {Math.round(log.confidence_score * 100)}%
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-2 text-[11px] text-white/70">
                {log.output_summary}
              </div>

              {log.rationale && (
                <div className="mt-1 text-[10px] text-white/50 italic">
                  {log.rationale}
                </div>
              )}

              {routingEntry && routingEntry.override && (
                <div className="mt-2">
                  <RoutingDecisionBadge
                    llmSuggested={routingEntry.llm_next ?? undefined}
                    finalDecision={routingEntry.final}
                    overrideReason={routingEntry.override}
                    confidence={routingEntry.confidence ?? undefined}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Routing Trace Summary */}
      {routingTrace.length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/10">
          <div className="text-[10px] text-white/50 mb-2">Routing Decisions</div>
          <div className="flex flex-wrap gap-1">
            {routingTrace.map((entry, idx) => (
              <div
                key={idx}
                className={cn(
                  "text-[10px] px-2 py-1 rounded-full",
                  entry.override
                    ? "bg-amber-500/20 text-amber-300"
                    : "bg-cyan-500/20 text-cyan-300"
                )}
              >
                {formatAgentName(entry.from)} → {formatAgentName(entry.final)}
                {entry.override && " ⚠️"}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
