"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Auth Schemas
# ============================================================================


class LoginRequest(BaseModel):
    """Login request body."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response with JWT token."""

    access_token: str
    token_type: str = "bearer"
    role: str


class UserInfo(BaseModel):
    """Current user information."""

    user_id: str
    username: str
    role: str


# ============================================================================
# Disruption Schemas
# ============================================================================


class DisruptionCreate(BaseModel):
    """Request to create a new disruption."""

    type: str = Field(..., pattern="^(late_truck|stockout|machine_down)$")
    severity: int = Field(..., ge=1, le=5)
    details_json: dict[str, Any]


class DisruptionResponse(BaseModel):
    """Disruption detail response."""

    id: str
    type: str
    severity: int
    timestamp: datetime
    details_json: dict[str, Any]
    status: str

    class Config:
        from_attributes = True


# ============================================================================
# Pipeline Schemas
# ============================================================================


class PipelineRunRequest(BaseModel):
    """Request to start a pipeline run."""

    disruption_id: str = Field(..., min_length=1)


class PipelineRunResponse(BaseModel):
    """Response after starting a pipeline run."""

    pipeline_run_id: str


class PipelineStatusResponse(BaseModel):
    """Pipeline run status response."""

    pipeline_run_id: str
    disruption_id: str
    status: str
    current_step: Optional[str] = None
    progress: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    final_summary_json: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Scenario Schemas
# ============================================================================


class ScenarioResponse(BaseModel):
    """Scenario detail response."""

    scenario_id: str
    disruption_id: str
    order_id: str
    action_type: str
    plan_json: dict[str, Any]
    score_json: dict[str, Any]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScenarioPendingResponse(BaseModel):
    """Pending scenario with joined disruption and order info."""

    scenario_id: str
    disruption_id: str
    order_id: str
    action_type: str
    plan_json: dict[str, Any]
    score_json: dict[str, Any]
    status: str
    created_at: datetime
    # Joined data
    disruption_type: str
    disruption_severity: int
    order_priority: str
    order_dc: str

    class Config:
        from_attributes = True


class ApproveRejectRequest(BaseModel):
    """Request to approve or reject a scenario."""

    note: str = Field(..., min_length=1)


class EditScenarioRequest(BaseModel):
    """Request to edit a scenario."""

    override_plan_json: dict[str, Any]
    note: str = Field(..., min_length=1)


class ApprovalResponse(BaseModel):
    """Response after approving a scenario."""

    scenario_id: str
    status: str
    applied_changes: dict[str, Any]
    decision_log_id: str


class RejectionResponse(BaseModel):
    """Response after rejecting a scenario."""

    scenario_id: str
    status: str
    decision_log_id: str


class EditResponse(BaseModel):
    """Response after editing a scenario."""

    scenario_id: str
    status: str
    updated_plan_json: dict[str, Any]
    updated_score_json: dict[str, Any]
    decision_log_id: str


# ============================================================================
# Audit Log Schemas
# ============================================================================


class DecisionLogResponse(BaseModel):
    """Decision log entry response."""

    log_id: str
    timestamp: str
    pipeline_run_id: str
    agent_name: str
    input_summary: str
    output_summary: str
    confidence_score: float
    rationale: str
    human_decision: str
    approver_id: Optional[str] = None
    approver_note: Optional[str] = None
    override_value: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============================================================================
# Dashboard Schemas
# ============================================================================


class DashboardResponse(BaseModel):
    """Dashboard summary response."""

    active_disruptions_count: int
    pending_scenarios_count: int
    approval_queue_count: int
    avg_sla_risk_pending: float
    estimated_cost_impact_pending: float
    recent_decisions: list[DecisionLogResponse]


# ============================================================================
# Error Schemas
# ============================================================================


class ErrorDetail(BaseModel):
    """Standard error response structure."""

    code: str
    message: str
    meta: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response wrapper."""

    error: ErrorDetail
