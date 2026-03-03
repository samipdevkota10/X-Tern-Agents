"use client";

import type { LucideIcon } from "lucide-react";

import { GlassCard } from "@/components/shared/GlassCard";
import { Button } from "@/components/ui/button";

export function EmptyState(props: {
  icon: LucideIcon;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const Icon = props.icon;

  return (
    <GlassCard className="p-8 text-center flex flex-col items-center gap-3">
      <div className="h-12 w-12 rounded-2xl bg-cyan-400/10 border border-cyan-400/20 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.25)]">
        <Icon className="h-6 w-6 text-cyan-200" />
      </div>
      <div className="text-sm font-semibold text-white">{props.title}</div>
      {props.description ? (
        <div className="text-xs text-white/60 max-w-md">{props.description}</div>
      ) : null}
      {props.actionLabel && props.onAction ? (
        <Button
          onClick={props.onAction}
          className="mt-2 rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200"
        >
          {props.actionLabel}
        </Button>
      ) : null}
    </GlassCard>
  );
}

