"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

export function GlassCard({
  className,
  glow,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  return (
    <div
      className={cn(
        "glass-card glass-hover-border transition-all duration-200",
        glow && "glow-cyan",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

