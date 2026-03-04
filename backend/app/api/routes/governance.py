"""
AI Governance API routes.
Implements AI TRiSM (Trust, Risk, Security Management) endpoints.
"""
import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.db.models import DecisionLog, PipelineRun, Scenario, User
from app.governance.trism import AIGovernanceFramework, get_governance_framework
from app.agents.security import AgentSecurityGuard, get_security_guard

router = APIRouter(prefix="/api/governance", tags=["governance"])


# Response models
class TrustMetrics(BaseModel):
    explainability_score: float
    consistency_score: float
    human_override_rate: float
    rationale_provided: bool
    findings: list[str]


class RiskMetrics(BaseModel):
    level: str
    harm_category: str
    confidence_threshold_met: bool
    max_cost_impact_usd: float
    max_sla_risk: float
    findings: list[str]


class SecurityMetrics(BaseModel):
    data_lineage_tracked: bool
    pii_detected: bool
    prompt_injection_detected: bool
    input_sanitized: bool
    output_validated: bool
    findings: list[str]


class ManagementMetrics(BaseModel):
    approval_required: bool
    escalation_path: Optional[str]
    evaluated_by: str


class TRiSMResponse(BaseModel):
    evaluation_id: str
    pipeline_run_id: str
    evaluated_at: str
    trust: TrustMetrics
    risk: RiskMetrics
    security: SecurityMetrics
    management: ManagementMetrics


class SecurityCheckResponse(BaseModel):
    passed: bool
    check_name: str
    violations: list[str]
    checked_at: str


class ApprovalPathResponse(BaseModel):
    auto_approve: bool
    required_role: Optional[str]
    escalation_chain: list[str]
    reason: str
    priority: str


@router.get("/trism/{pipeline_run_id}", response_model=TRiSMResponse)
def get_trism_evaluation(
    pipeline_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get AI TRiSM (Trust, Risk, Security Management) evaluation for a pipeline run.
    
    This endpoint performs a comprehensive governance evaluation including:
    - Trust: Explainability, consistency, human override rates
    - Risk: Risk level, cost impact, SLA risk assessment
    - Security: PII detection, prompt injection checks, data lineage
    - Management: Approval requirements and escalation paths
    
    Args:
        pipeline_run_id: The pipeline run to evaluate
        
    Returns:
        TRiSMResponse with full evaluation metrics
    """
    # Verify pipeline run exists
    pipeline_run = db.query(PipelineRun).filter(
        PipelineRun.pipeline_run_id == pipeline_run_id
    ).first()
    
    if not pipeline_run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    # Fetch scenarios for this pipeline run (via disruption_id)
    scenarios = db.query(Scenario).filter(
        Scenario.disruption_id == pipeline_run.disruption_id
    ).all()
    
    # Convert scenarios to dict format
    scenarios_data = []
    for s in scenarios:
        score_json = {}
        try:
            score_json = json.loads(s.score_json) if s.score_json else {}
        except (json.JSONDecodeError, TypeError):
            pass
        
        plan_json = {}
        try:
            plan_json = json.loads(s.plan_json) if s.plan_json else {}
        except (json.JSONDecodeError, TypeError):
            pass
            
        scenarios_data.append({
            "scenario_id": s.scenario_id,
            "action_type": s.action_type,
            "status": s.status,
            "plan_json": plan_json,
            "score_json": score_json,
        })
    
    # Fetch decision logs for this pipeline run
    decision_logs = db.query(DecisionLog).filter(
        DecisionLog.pipeline_run_id == pipeline_run_id
    ).all()
    
    # Convert logs to dict format
    logs_data = []
    for log in decision_logs:
        override_value = None
        try:
            override_value = json.loads(log.override_value) if log.override_value else None
        except (json.JSONDecodeError, TypeError):
            pass
            
        logs_data.append({
            "log_id": log.log_id,
            "timestamp": log.timestamp,
            "agent_name": log.agent_name,
            "input_summary": log.input_summary,
            "output_summary": log.output_summary,
            "confidence_score": log.confidence_score,
            "rationale": log.rationale,
            "human_decision": log.human_decision,
            "override_value": override_value,
        })
    
    # Perform TRiSM evaluation
    framework = get_governance_framework()
    evaluation = framework.evaluate_pipeline_run(
        pipeline_run_id=pipeline_run_id,
        scenarios=scenarios_data,
        decision_logs=logs_data,
    )
    
    return evaluation.to_dict()


@router.get("/trism", response_model=list[TRiSMResponse])
def list_trism_evaluations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by pipeline status: done, running, failed"),
) -> list[dict]:
    """
    List TRiSM evaluations for recent pipeline runs.
    
    Returns evaluations for the most recent pipeline runs, optionally filtered by status.
    """
    query = db.query(PipelineRun)
    
    if status:
        query = query.filter(PipelineRun.status == status)
    
    pipeline_runs = query.order_by(
        PipelineRun.started_at.desc()
    ).limit(limit).all()
    
    framework = get_governance_framework()
    evaluations = []
    
    for run in pipeline_runs:
        # Fetch data for each run
        scenarios = db.query(Scenario).filter(
            Scenario.disruption_id == run.disruption_id
        ).all()
        
        scenarios_data = []
        for s in scenarios:
            score_json = {}
            try:
                score_json = json.loads(s.score_json) if s.score_json else {}
            except (json.JSONDecodeError, TypeError):
                pass
                
            scenarios_data.append({
                "scenario_id": s.scenario_id,
                "action_type": s.action_type,
                "status": s.status,
                "score_json": score_json,
            })
        
        logs = db.query(DecisionLog).filter(
            DecisionLog.pipeline_run_id == run.pipeline_run_id
        ).all()
        
        logs_data = [
            {
                "agent_name": log.agent_name,
                "confidence_score": log.confidence_score,
                "rationale": log.rationale,
                "timestamp": log.timestamp,
            }
            for log in logs
        ]
        
        evaluation = framework.evaluate_pipeline_run(
            pipeline_run_id=run.pipeline_run_id,
            scenarios=scenarios_data,
            decision_logs=logs_data,
        )
        evaluations.append(evaluation.to_dict())
    
    return evaluations


@router.post("/security/validate-scenario/{scenario_id}", response_model=SecurityCheckResponse)
def validate_scenario_security(
    scenario_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Validate a scenario against security bounds.
    
    Checks:
    - Cost impact within limits
    - SLA risk within valid range
    - Action type is whitelisted
    - Required fields present
    """
    scenario = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Convert to dict
    score_json = {}
    try:
        score_json = json.loads(scenario.score_json) if scenario.score_json else {}
    except (json.JSONDecodeError, TypeError):
        pass
    
    plan_json = {}
    try:
        plan_json = json.loads(scenario.plan_json) if scenario.plan_json else {}
    except (json.JSONDecodeError, TypeError):
        pass
    
    scenario_data = {
        "scenario_id": scenario.scenario_id,
        "action_type": scenario.action_type,
        "status": scenario.status,
        "plan_json": plan_json,
        "score_json": score_json,
    }
    
    security_guard = get_security_guard()
    result = security_guard.validate_scenario_bounds(scenario_data)
    
    return result.to_dict()


@router.get("/security/approval-path/{scenario_id}", response_model=ApprovalPathResponse)
def get_approval_path(
    scenario_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Determine the required approval path for a scenario.
    
    Based on cost impact and SLA risk, determines:
    - Whether auto-approval is allowed
    - Required role for approval
    - Escalation chain
    """
    scenario = db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Convert to dict
    score_json = {}
    try:
        score_json = json.loads(scenario.score_json) if scenario.score_json else {}
    except (json.JSONDecodeError, TypeError):
        pass
    
    scenario_data = {
        "score_json": score_json,
    }
    
    security_guard = get_security_guard()
    return security_guard.determine_approval_path(scenario_data)


@router.post("/security/validate-agent-chain/{pipeline_run_id}", response_model=SecurityCheckResponse)
def validate_agent_chain(
    pipeline_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Validate that agents executed in proper sequence for a pipeline run.
    
    Ensures:
    - Agents executed in expected order
    - No unauthorized agents participated
    - Chain integrity maintained
    """
    # Verify pipeline run exists
    pipeline_run = db.query(PipelineRun).filter(
        PipelineRun.pipeline_run_id == pipeline_run_id
    ).first()
    
    if not pipeline_run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    
    # Fetch decision logs
    logs = db.query(DecisionLog).filter(
        DecisionLog.pipeline_run_id == pipeline_run_id
    ).all()
    
    logs_data = [
        {
            "agent_name": log.agent_name,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]
    
    security_guard = get_security_guard()
    result = security_guard.validate_agent_chain(logs_data)
    
    return result.to_dict()


@router.get("/summary")
def get_governance_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get a summary of governance metrics across all recent pipeline runs.
    
    Returns aggregate statistics for monitoring AI governance health.
    """
    # Get recent pipeline runs
    recent_runs = db.query(PipelineRun).order_by(
        PipelineRun.started_at.desc()
    ).limit(50).all()
    
    if not recent_runs:
        return {
            "total_runs_evaluated": 0,
            "risk_distribution": {},
            "approval_rate": 0.0,
            "average_confidence": 0.0,
            "security_incidents": 0,
        }
    
    framework = get_governance_framework()
    
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    total_confidence = 0.0
    confidence_count = 0
    approval_required_count = 0
    pii_incidents = 0
    injection_incidents = 0
    
    for run in recent_runs:
        scenarios = db.query(Scenario).filter(
            Scenario.disruption_id == run.disruption_id
        ).all()
        
        scenarios_data = []
        for s in scenarios:
            score_json = {}
            try:
                score_json = json.loads(s.score_json) if s.score_json else {}
            except (json.JSONDecodeError, TypeError):
                pass
            scenarios_data.append({
                "action_type": s.action_type,
                "status": s.status,
                "score_json": score_json,
            })
        
        logs = db.query(DecisionLog).filter(
            DecisionLog.pipeline_run_id == run.pipeline_run_id
        ).all()
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "agent_name": log.agent_name,
                "confidence_score": log.confidence_score,
                "rationale": log.rationale,
            })
            if log.confidence_score:
                total_confidence += log.confidence_score
                confidence_count += 1
        
        evaluation = framework.evaluate_pipeline_run(
            pipeline_run_id=run.pipeline_run_id,
            scenarios=scenarios_data,
            decision_logs=logs_data,
        )
        
        risk_counts[evaluation.risk_level.value] += 1
        if evaluation.approval_required:
            approval_required_count += 1
        if evaluation.pii_detected:
            pii_incidents += 1
        if evaluation.prompt_injection_detected:
            injection_incidents += 1
    
    return {
        "total_runs_evaluated": len(recent_runs),
        "risk_distribution": risk_counts,
        "approval_required_rate": approval_required_count / len(recent_runs) if recent_runs else 0,
        "average_confidence": total_confidence / confidence_count if confidence_count > 0 else 0,
        "security_incidents": {
            "pii_detected": pii_incidents,
            "prompt_injection_detected": injection_incidents,
            "total": pii_incidents + injection_incidents,
        },
        "governance_health": "healthy" if (pii_incidents + injection_incidents) == 0 else "attention_needed",
    }
