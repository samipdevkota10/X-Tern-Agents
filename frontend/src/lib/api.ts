/**
 * API client for backend communication
 */

import type {
  DashboardResponse,
  DecisionLogEntry,
  Disruption,
  DisruptionCreateRequest,
  LoginResponse,
  PendingScenarioRow,
  PipelineRunStatus,
  Scenario,
  UserInfo,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

/**
 * Get stored auth token
 */
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

/**
 * Make authenticated API request
 */
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    if (res.status === 401 && !path.includes("/auth/login") && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
      throw new Error("Session expired. Please log in again.");
    }
    const errorBody = await res.json().catch(() => ({}));
    // Backend uses detail.error.message or detail as string/array (FastAPI)
    const msg =
      errorBody.detail?.error?.message ??
      (typeof errorBody.detail === "string" ? errorBody.detail : null) ??
      errorBody.error?.message ??
      (Array.isArray(errorBody.detail) ? errorBody.detail[0]?.msg : null) ??
      `API Error: ${res.status}`;
    throw new Error(msg);
  }

  return res.json();
}

// ============================================================================
// Auth API
// ============================================================================

const LOGIN_TIMEOUT_MS = 15_000;

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), LOGIN_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || "Login failed");
    }

    return res.json();
  } catch (e) {
    if (e instanceof Error) {
      if (e.name === "AbortError") {
        throw new Error("Login timed out. Is the backend running at " + API_BASE + "?");
      }
      throw e;
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout", { method: "POST" });
}

export async function getCurrentUser(): Promise<UserInfo> {
  return apiFetch<UserInfo>("/api/auth/me");
}

// ============================================================================
// Disruptions API
// ============================================================================

export async function listDisruptions(params?: {
  status?: string;
  limit?: number;
}): Promise<Disruption[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));

  const qs = query.toString();
  return apiFetch<Disruption[]>(`/api/disruptions${qs ? `?${qs}` : ""}`);
}

export async function getDisruption(id: string): Promise<Disruption> {
  return apiFetch<Disruption>(`/api/disruptions/${id}`);
}

export async function createDisruption(
  data: DisruptionCreateRequest
): Promise<Disruption> {
  return apiFetch<Disruption>("/api/disruptions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateDisruptionStatus(
  id: string,
  status: "open" | "resolved"
): Promise<Disruption> {
  return apiFetch<Disruption>(`/api/disruptions/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// ============================================================================
// Scenarios API
// ============================================================================

export async function listScenarios(params?: {
  disruption_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<Scenario[]> {
  const query = new URLSearchParams();
  if (params?.disruption_id) query.set("disruption_id", params.disruption_id);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiFetch<Scenario[]>(`/api/scenarios${qs ? `?${qs}` : ""}`);
}

export async function listPendingScenarios(): Promise<PendingScenarioRow[]> {
  return apiFetch<PendingScenarioRow[]>("/api/scenarios/pending");
}

export async function getScenario(id: string): Promise<Scenario> {
  return apiFetch<Scenario>(`/api/scenarios/${id}`);
}

export async function approveScenario(
  scenarioId: string,
  note: string
): Promise<{ scenario_id: string; status: string; decision_log_id: string }> {
  return apiFetch(`/api/scenarios/${scenarioId}/approve`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function rejectScenario(
  scenarioId: string,
  note: string
): Promise<{ scenario_id: string; status: string; decision_log_id: string }> {
  return apiFetch(`/api/scenarios/${scenarioId}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function editScenario(
  scenarioId: string,
  overridePlanJson: Record<string, unknown>,
  note: string
): Promise<{
  scenario_id: string;
  status: string;
  updated_plan_json: Record<string, unknown>;
}> {
  return apiFetch(`/api/scenarios/${scenarioId}/edit`, {
    method: "POST",
    body: JSON.stringify({ override_plan_json: overridePlanJson, note }),
  });
}

// ============================================================================
// Pipeline API
// ============================================================================

export async function startPipeline(
  disruptionId: string
): Promise<{ pipeline_run_id: string }> {
  return apiFetch("/api/pipeline/run", {
    method: "POST",
    body: JSON.stringify({ disruption_id: disruptionId }),
  });
}

export async function getPipelineStatus(
  pipelineRunId: string
): Promise<PipelineRunStatus> {
  return apiFetch<PipelineRunStatus>(`/api/pipeline/${pipelineRunId}/status`);
}

// ============================================================================
// Dashboard API
// ============================================================================

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/api/dashboard");
}

// ============================================================================
// Audit Logs API
// ============================================================================

export async function listAuditLogs(params?: {
  pipeline_run_id?: string;
  agent_name?: string;
  limit?: number;
}): Promise<DecisionLogEntry[]> {
  const query = new URLSearchParams();
  if (params?.pipeline_run_id)
    query.set("pipeline_run_id", params.pipeline_run_id);
  if (params?.agent_name) query.set("agent_name", params.agent_name);
  if (params?.limit) query.set("limit", String(params.limit));

  const qs = query.toString();
  return apiFetch<DecisionLogEntry[]>(`/api/audit-logs${qs ? `?${qs}` : ""}`);
}
