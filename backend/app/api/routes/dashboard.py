"""
Dashboard summary endpoint.
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.schemas import DashboardResponse, DecisionLogResponse
from app.core.deps import get_current_user, get_db
from app.db.models import DecisionLog, Disruption, Order, Scenario, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardResponse:
    """
    Get dashboard summary with key metrics and recent decisions.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Dashboard summary with counts, metrics, and recent decisions
    """
    # Active disruptions count
    active_disruptions_count = (
        db.query(func.count(Disruption.id))
        .filter(Disruption.status == "open")
        .scalar()
    ) or 0

    # Pending scenarios count
    pending_scenarios_count = (
        db.query(func.count(Scenario.scenario_id))
        .filter(Scenario.status == "pending")
        .scalar()
    ) or 0

    # Get pending scenarios with scores to calculate metrics
    pending_scenarios = (
        db.query(Scenario, Order)
        .join(Order, Scenario.order_id == Order.order_id)
        .filter(Scenario.status == "pending")
        .all()
    )

    # Calculate approval queue count and metrics
    approval_queue_count = 0
    total_sla_risk = 0.0
    total_cost = 0.0
    count_with_scores = 0

    for scenario, order in pending_scenarios:
        try:
            score = json.loads(scenario.score_json)
            sla_risk = score.get("sla_risk", 0.0)
            cost = score.get("cost_impact_usd", 0.0)

            total_sla_risk += sla_risk
            total_cost += cost
            count_with_scores += 1

            # Check if needs approval
            needs_approval = (
                sla_risk > 0.6
                or cost > 500
                or order.priority == "vip"
                or scenario.action_type == "substitute"
            )

            if needs_approval:
                approval_queue_count += 1

        except (json.JSONDecodeError, KeyError):
            # Skip scenarios with invalid scores
            continue

    # Calculate averages
    avg_sla_risk_pending = (
        round(total_sla_risk / count_with_scores, 3) if count_with_scores > 0 else 0.0
    )
    estimated_cost_impact_pending = round(total_cost, 2)

    # Get recent decisions (last 10)
    recent_logs = (
        db.query(DecisionLog)
        .order_by(DecisionLog.timestamp.desc())
        .limit(10)
        .all()
    )

    recent_decisions = [
        DecisionLogResponse(
            log_id=log.log_id,
            timestamp=log.timestamp,
            pipeline_run_id=log.pipeline_run_id,
            agent_name=log.agent_name,
            input_summary=log.input_summary,
            output_summary=log.output_summary,
            confidence_score=log.confidence_score,
            rationale=log.rationale,
            human_decision=log.human_decision,
            approver_id=log.approver_id,
            approver_note=log.approver_note,
            override_value=(
                json.loads(log.override_value) if log.override_value else None
            ),
        )
        for log in recent_logs
    ]

    return DashboardResponse(
        active_disruptions_count=active_disruptions_count,
        pending_scenarios_count=pending_scenarios_count,
        approval_queue_count=approval_queue_count,
        avg_sla_risk_pending=avg_sla_risk_pending,
        estimated_cost_impact_pending=estimated_cost_impact_pending,
        recent_decisions=recent_decisions,
    )
