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
  const key = ["scenarios", query] as const;

  const { data, error, isLoading, mutate } = useSWR<Scenario[]>(
    key,
    async () => {
      return listScenarios(query);
    },
    { refreshInterval: 15000 },
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
    async () => listPendingScenarios(),
    { refreshInterval: 10000 },
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

