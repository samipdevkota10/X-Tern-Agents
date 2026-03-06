/**
 * Type definitions matching backend Pydantic schemas
 */

// ============================================================================
// Auth Types
// ============================================================================

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface UserInfo {
  user_id: string;
  username: string;
  role: string;
}

// ============================================================================
// Disruption Types
// ============================================================================

export interface Disruption {
  id: string;
  type: DisruptionType;
  severity: number;
  timestamp: string;
  details_json: Record<string, unknown>;
  status: "open" | "resolved";
}

export type DisruptionType = "late_truck" | "stockout" | "machine_down";

export interface DisruptionCreateRequest {
  type: DisruptionType;
  severity: number;
  details_json: Record<string, unknown>;
}

// ============================================================================
// Scenario Types
// ============================================================================

export type ScenarioActionType =
  | "delay"
  | "reroute"
  | "substitute"
  | "resequence"
  | "expedite"
  | "split";

export interface ScoreJson {
  sla_risk: number;
  cost_impact_usd: number;
  complexity: number;
  overall_score: number;
  labor_impact_minutes?: number;
  needs_approval?: boolean;
}

// Alias for backwards compatibility
export type ScenarioScore = ScoreJson;

export interface PlanJson {
  action?: ScenarioActionType;
  summary?: string;
  what_happened?: string;
  what_to_do?: string;
  how_to_handle?: string;
  rationale?: string;
  details?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface Scenario {
  scenario_id: string;
  disruption_id: string;
  order_id: string;
  action_type: ScenarioActionType;
  plan_json: PlanJson;
  score_json: ScoreJson;
  status: "pending" | "approved" | "rejected" | "executed";
  created_at: string;
  llm_rationale?: string;  // LLM-generated reasoning when AWS Bedrock is used
  used_llm?: boolean;      // Whether LLM was used for this scenario
}

export interface PendingScenarioRow extends Scenario {
  disruption_type: string;
  disruption_severity: number;
  order_priority: string;
  order_dc: string;
}

// ============================================================================
// Pipeline Types
// ============================================================================

export interface PipelineRunStatus {
  pipeline_run_id: string;
  disruption_id: string;
  status: "pending" | "queued" | "running" | "completed" | "failed" | "needs_review" | "done";
  current_step?: string;
  progress: number;
  started_at: string;
  completed_at?: string;
  final_summary_json?: Record<string, unknown>;
  error_message?: string;
}

// ============================================================================
// Audit Log Types
// ============================================================================

export type DecisionType = "pending" | "approved" | "rejected" | "auto_approved";

export interface DecisionLogEntry {
  log_id: string;
  timestamp: string;
  pipeline_run_id: string;
  agent_name: string;
  input_summary: string;
  output_summary: string;
  confidence_score: number;
  rationale: string;
  human_decision: DecisionType;
  approver_id?: string;
  approver_note?: string;
  override_value?: Record<string, unknown>;
}

// ============================================================================
// Dashboard Types
// ============================================================================

export interface DashboardResponse {
  active_disruptions_count: number;
  pending_scenarios_count: number;
  approval_queue_count: number;
  avg_sla_risk_pending: number;
  estimated_cost_impact_pending: number;
  recent_decisions: DecisionLogEntry[];
}
