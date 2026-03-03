"use client";

import * as React from "react";
import { LockKeyhole, User } from "lucide-react";

import { useAuth } from "@/lib/auth";
import { GlassCard } from "@/components/shared/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const { login, loading } = useAuth();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setSubmitting(true);
    try {
      await login(username, password);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <GlassCard glow className="w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="h-10 w-10 rounded-2xl bg-cyan-400/10 border border-cyan-400/20 flex items-center justify-center shadow-[0_0_20px_rgba(34,211,238,0.25)]">
            <LockKeyhole className="h-5 w-5 text-cyan-200" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Sign in to DisruptIQ</div>
            <div className="text-[11px] text-white/50">JWT auth backed by FastAPI.</div>
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <div className="text-[11px] text-white/60 mb-1">Username</div>
            <div className="relative">
              <User className="absolute left-3 top-2.5 h-4 w-4 text-white/30" />
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="manager_01"
                className="h-9 pl-10 bg-black/30 border-white/10 text-white placeholder:text-white/30 focus-visible:ring-cyan-400/30"
                autoComplete="username"
              />
            </div>
          </div>

          <div>
            <div className="text-[11px] text-white/60 mb-1">Password</div>
            <div className="relative">
              <LockKeyhole className="absolute left-3 top-2.5 h-4 w-4 text-white/30" />
              <Input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="password"
                type="password"
                className="h-9 pl-10 bg-black/30 border-white/10 text-white placeholder:text-white/30 focus-visible:ring-cyan-400/30"
                autoComplete="current-password"
              />
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading || submitting || !username || !password}
            className="w-full rounded-full bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)] transition-all duration-200"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </Button>

          <div className="mt-4 text-[11px] text-white/50">
            Demo users: <span className="text-white/70">manager_01 / password</span>{" "}
            • <span className="text-white/70">analyst_01 / password</span>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}

