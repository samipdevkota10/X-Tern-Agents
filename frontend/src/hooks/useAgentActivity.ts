"use client";

import useSWR from "swr";

import type { DecisionLogEntry } from "@/lib/types";
import { listAuditLogs } from "@/lib/api";

export interface RoutingTraceEntry {
  ts: string;
  from: string;
  llm_next: string | null;
  final: string;
  override: string | null;
  confidence: number | null;
  reason: string | null;
}

export interface AgentActivityData {
  decisionLogs: DecisionLogEntry[];
  routingTrace: RoutingTraceEntry[];
  isRunning: boolean;
}

/**
 * Hook to fetch agent activity for a pipeline run.
 * Combines decision logs with routing trace from pipeline status.
 */
export function useAgentActivity(runId?: string | null, isRunning?: boolean) {
  // Fetch decision logs for this pipeline run
  const { data: logs, error, isLoading, mutate } = useSWR<DecisionLogEntry[]>(
    runId ? ["agent-activity", runId] : null,
    async () => listAuditLogs({ pipeline_run_id: runId as string, limit: 50 }),
    {
      refreshInterval: isRunning ? 2000 : 0,
    },
  );

  return {
    logs: logs ?? [],
    isLoading: Boolean(runId) && isLoading,
    error,
    mutate,
  };
}
