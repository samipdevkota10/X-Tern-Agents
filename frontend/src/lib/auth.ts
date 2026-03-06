"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { jwtDecode } from "jwt-decode";

import type { LoginRequest, LoginResponse, UserMe, UserRole } from "@/lib/types";
import * as api from "@/lib/api";

const TOKEN_KEY = "disruptiq_token";
const ROLE_KEY = "disruptiq_role";

type JwtPayload = {
  sub?: string;
  role?: UserRole;
  exp?: number;
};

export type AuthState = {
  token: string | null;
  role: UserRole | null;
  user: UserMe | null;
  isManager: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<LoginResponse | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

function readLocalAuth(): { token: string | null; role: UserRole | null } {
  if (typeof window === "undefined") return { token: null, role: null };
  const token = localStorage.getItem(TOKEN_KEY);
  const role = (localStorage.getItem(ROLE_KEY) as UserRole | null) ?? null;
  return { token, role };
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = jwtDecode<JwtPayload>(token);
    if (!payload.exp) return false;
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

export function AuthProvider(props: { children: React.ReactNode }) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(ROLE_KEY);
    }
    setToken(null);
    setRole(null);
    setUser(null);
    router.replace("/login");
  }, [router]);

  const login = useCallback(
    async (username: string, password: string) => {
      try {
        const res = await api.login({ username, password } satisfies LoginRequest);
        setToken(res.access_token);
        setRole(res.role);
        const me = await api.me();
        setUser(me);
        toast.success("Welcome to DisruptIQ.");
        router.replace("/dashboard");
        return res;
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Login failed";
        toast.error(msg);
        return null;
      }
    },
    [router],
  );

  // bootstrap auth
  useEffect(() => {
    const { token: t, role: r } = readLocalAuth();
    if (!t) {
      setLoading(false);
      return;
    }
    if (isTokenExpired(t)) {
      toast.error("Session expired. Please log in again.");
      logout();
      setLoading(false);
      return;
    }

    setToken(t);
    setRole(r);

    api
      .me()
      .then((meRes) => setUser(meRes))
      .catch(() => {
        toast.error("Session invalid. Please log in again.");
        logout();
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<AuthState>(() => {
    return {
      token,
      role,
      user,
      loading,
      isManager: role === "warehouse_manager",
      login,
      logout,
    };
  }, [token, role, user, loading, login, logout]);

  // no JSX in .ts file
  return React.createElement(AuthContext.Provider, { value }, props.children);
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export function useRequireAuth() {
  const router = useRouter();
  const { token, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (!token) router.replace("/login");
  }, [token, loading, router]);
}

