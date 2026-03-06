"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { toast } from "sonner";
import { getPipelineStatus } from "@/lib/api";
import type { PipelineRunStatus } from "@/lib/types";
import {
  getStoredPipelineRunId,
  clearStoredPipelineRunId,
} from "@/hooks/usePipelineStatus";

/**
 * Polls for active pipeline run when user is on a different page.
 * Shows toast when pipeline completes or fails, so user gets notified
 * even when switching tabs or navigating away from Run Planner.
 * Skips when on /run page (Run page handles its own toast).
 */
export function PipelineCompletionNotifier() {
  const pathname = usePathname();
  const isOnRunPage = pathname?.startsWith("/run");
  const [runId, setRunId] = React.useState<string | null>(null);

  // Sync runId from localStorage (e.g. when Run page starts a pipeline)
  React.useEffect(() => {
    const check = () => {
      const stored = getStoredPipelineRunId();
      if (stored && stored !== runId) setRunId(stored);
      if (!stored && runId) setRunId(null);
    };
    check();
    const id = setInterval(check, 1000);
    return () => clearInterval(id);
  }, [runId]);

  const { data } = useSWR<PipelineRunStatus>(
    runId && !isOnRunPage ? ["pipeline-notifier", runId] : null,
    () => getPipelineStatus(runId!),
    {
      refreshInterval: (latest) => {
        if (!latest) return 2000;
        const s = latest.status;
        if (s === "done" || s === "needs_review" || s === "completed" || s === "failed") {
          return 0;
        }
        return 2000;
      },
      refreshWhenHidden: true,
    }
  );

  const prevStatusRef = React.useRef<string | undefined>(undefined);

  React.useEffect(() => {
    if (!data || !runId) return;
    const s = data.status;
    const wasRunning =
      prevStatusRef.current === "running" ||
      prevStatusRef.current === "queued" ||
      prevStatusRef.current === "pending";

    if (s === "done" || s === "needs_review" || s === "completed") {
      if (wasRunning) {
        const count = (data.final_summary_json as Record<string, unknown>)
          ?.scenarios_count as number | undefined;
        toast.success(
          `Pipeline complete! ${typeof count === "number" ? `${count} scenarios` : "Scenarios"} generated.`,
          { duration: 5000 }
        );
        clearStoredPipelineRunId();
        setRunId(null);
      }
      prevStatusRef.current = s;
    } else if (s === "failed") {
      if (wasRunning) {
        toast.error("Pipeline failed. Check Run Planner for details.");
        clearStoredPipelineRunId();
        setRunId(null);
      }
      prevStatusRef.current = s;
    } else {
      prevStatusRef.current = s;
    }
  }, [data, runId]);

  return null;
}
