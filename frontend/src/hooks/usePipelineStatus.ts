"use client";

import useSWR from "swr";

import type { PipelineRunStatus } from "@/lib/types";
import { getPipelineStatus } from "@/lib/api";

export function usePipelineStatus(runId?: string | null) {
  const { data, error, isLoading, mutate } = useSWR<PipelineRunStatus>(
    runId ? ["pipeline-status", runId] : null,
    async () => getPipelineStatus(runId as string),
    {
      refreshInterval: (latest) => {
        if (!latest) return 0;
        return latest.status === "running" || latest.status === "queued" ? 2000 : 0;
      },
    },
  );

  return {
    status: data ?? null,
    isLoading: Boolean(runId) && isLoading,
    error,
    mutate,
  };
}

