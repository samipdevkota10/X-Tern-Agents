/**
 * Type definitions for the X-Tern Agents application
 */

export interface Decision {
  id: string;
  decision: string;
  made_by: string;
  reason?: string;
  timestamp: string;
  approved: boolean;
}

export interface Case {
  id: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  assigned_to?: string;
  decisions: Decision[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CaseCreate {
  title: string;
  description: string;
  priority?: string;
  assigned_to?: string;
  metadata?: Record<string, unknown>;
}

export interface DecisionCreate {
  decision: string;
  made_by: string;
  reason?: string;
  approved?: boolean;
}

export interface CaseListResponse {
  cases: Case[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}

export interface RiskScore {
  risk_score: number;
  risk_level: string;
  factors_evaluated: string[];
  recommendations: string[];
}
