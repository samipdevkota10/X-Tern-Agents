"use client";

import { cn } from "@/lib/utils";

export function KpiCardSkeleton() {
  return <div className="glass-card glass-skeleton h-[110px] w-full rounded-2xl" />;
}

export function TableSkeleton(props: { rows?: number; className?: string }) {
  const rows = props.rows ?? 6;
  return (
    <div className={cn("glass-card p-4", props.className)}>
      <div className="mb-4 h-5 w-40 rounded-full glass-skeleton" />
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-9 w-full rounded-xl glass-skeleton" />
        ))}
      </div>
    </div>
  );
}

export function CardGridSkeleton(props: { count?: number }) {
  const count = props.count ?? 6;
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass-card glass-skeleton h-44 rounded-2xl" />
      ))}
    </div>
  );
}

