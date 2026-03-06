"use client";

import useSWR from "swr";

import type { PipelineRunStatus } from "@/lib/types";
import { getPipelineStatus } from "@/lib/api";

export const STORAGE_KEY = "activePipelineRunId";

export function getStoredPipelineRunId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

export function setStoredPipelineRunId(runId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, runId);
}

export function clearStoredPipelineRunId(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

export function usePipelineStatus(runId?: string | null) {
  const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
  const effectiveRunId = runId || stored;

  const { data, error, isLoading, mutate } = useSWR<PipelineRunStatus>(
    effectiveRunId ? ["pipeline-status", effectiveRunId] : null,
    async () => getPipelineStatus(effectiveRunId as string),
    {
      refreshInterval: (latest) => {
        if (!latest) return 0;
        return latest.status === "running" || latest.status === "queued" ? 2000 : 0;
      },
      // Keep polling even when tab is in background so pipeline progress persists
      refreshWhenHidden: true,
    },
  );

  return {
    status: data ?? null,
    isLoading: Boolean(effectiveRunId) && isLoading,
    error,
    mutate,
    runId: effectiveRunId,
  };
}

