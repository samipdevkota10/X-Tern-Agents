"use client";

import useSWR from "swr";

import type { PendingScenarioRow, Scenario } from "@/lib/types";
import { listPendingScenarios, listScenarios } from "@/lib/api";

export type ScenarioQuery = {
  disruption_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
};

export function useScenarios(query?: ScenarioQuery) {
  // Normalize query so key is stable (omit undefined values)
  const normalizedQuery = query
    ? Object.fromEntries(
        Object.entries(query).filter(([, v]) => v != null && v !== "")
      ) as ScenarioQuery
    : undefined;
  const key = ["scenarios", normalizedQuery] as const;

  const { data, error, isLoading, mutate } = useSWR<Scenario[]>(
    key,
    () => listScenarios(normalizedQuery),
    {
      refreshInterval: 15000,
      // Keep showing previous scenarios when switching tabs or refetching
      keepPreviousData: true,
      dedupingInterval: 5000,
    }
  );

  return {
    scenarios: data ?? [],
    isLoading,
    error,
    mutate,
  };
}

export function usePendingScenarios() {
  const { data, error, isLoading, mutate } = useSWR<PendingScenarioRow[]>(
    ["scenarios-pending"],
    () => listPendingScenarios(),
    {
      refreshInterval: 10000,
      keepPreviousData: true,
      dedupingInterval: 5000,
    },
  );

  // Pending endpoint returns enriched scenario rows
  const scenarios = (data ?? []) as unknown as Scenario[];

  return {
    scenarios,
    isLoading,
    error,
    mutate,
  };
}

export function usePendingApprovalsCount() {
  const { scenarios } = usePendingScenarios();
  return scenarios.filter((s) => s.status === "pending" && s.score_json?.needs_approval).length;
}

