"use client";

import useSWR from "swr";

import type { DecisionLogEntry } from "@/lib/types";
import { listAuditLogs } from "@/lib/api";

export type AuditLogFilters = {
  pipeline_run_id?: string;
  agent_name?: string;
  human_decision?: string;
  limit?: number;
  offset?: number;
};

export function useAuditLogs(filters?: AuditLogFilters) {
  const key = ["audit-logs", filters] as const;

  const { data, error, isLoading, mutate } = useSWR<DecisionLogEntry[]>(
    key,
    async () => listAuditLogs(filters),
    {
      refreshInterval: 0,
      revalidateOnFocus: true,
    },
  );

  return {
    logs: data ?? [],
    isLoading,
    error,
    mutate,
  };
}

