"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, login as apiLogin, logout as apiLogout } from "./api";
import type { UserInfo } from "./types";

interface AuthContextValue {
  user: UserInfo | null;
  isLoading: boolean;
  loading: boolean; // Alias for isLoading (backwards compatibility)
  role: string | null;
  isManager: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(
  undefined
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const router = useRouter();

  // Check for existing session on mount
  React.useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      getCurrentUser()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("token");
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = React.useCallback(
    async (username: string, password: string) => {
      const response = await apiLogin(username, password);
      localStorage.setItem("token", response.access_token);
      const userInfo = await getCurrentUser();
      setUser(userInfo);
      router.push("/dashboard");
    },
    [router]
  );

  const logout = React.useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem("token");
    setUser(null);
    router.push("/login");
  }, [router]);

  const role = user?.role ?? null;
  const isManager = role === "warehouse_manager";

  const value = React.useMemo(
    () => ({ user, isLoading, loading: isLoading, role, isManager, login, logout }),
    [user, isLoading, role, isManager, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context
 */
export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

/**
 * Hook that redirects to login if not authenticated
 */
export function useRequireAuth(): AuthContextValue {
  const auth = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!auth.isLoading && !auth.user) {
      router.push("/login");
    }
  }, [auth.isLoading, auth.user, router]);

  return auth;
}

/**
 * Hook that redirects to dashboard if already authenticated
 */
export function useRedirectIfAuth(): AuthContextValue {
  const auth = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!auth.isLoading && auth.user) {
      router.push("/dashboard");
    }
  }, [auth.isLoading, auth.user, router]);

  return auth;
}
