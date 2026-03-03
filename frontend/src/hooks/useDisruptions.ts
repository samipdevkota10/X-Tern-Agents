"use client";

import useSWR from "swr";

import type { Disruption } from "@/lib/types";
import { listDisruptions } from "@/lib/api";

export type DisruptionFilters = {
  status?: string;
  type?: string;
  severity?: number;
};

export function useDisruptions(filters?: DisruptionFilters) {
  const key = ["disruptions", filters] as const;

  const { data, error, isLoading, mutate } = useSWR<Disruption[]>(
    key,
    async () => {
      const all = await listDisruptions({ status: filters?.status });
      return all.filter((d) => {
        if (filters?.type && d.type !== filters.type) return false;
        if (filters?.severity && d.severity !== filters.severity) return false;
        return true;
      });
    },
    { refreshInterval: 15000 },
  );

  return {
    disruptions: data ?? [],
    isLoading,
    error,
    mutate,
  };
}

