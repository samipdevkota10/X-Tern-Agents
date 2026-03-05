"""
Scenario management routes with approval/rejection/editing.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ApprovalResponse,
    ApproveRejectRequest,
    EditResponse,
    EditScenarioRequest,
    RejectionResponse,
    ScenarioPendingResponse,
    ScenarioResponse,
)
from app.core.deps import get_current_user, get_db, require_role
from app.db.models import DecisionLog, Disruption, Order, Scenario, User
from app.services.execution_engine import apply_scenario

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    disruption_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[ScenarioResponse]:
    """
    List scenarios with optional filters and pagination.

    Args:
        db: Database session
        current_user: Current authenticated user
        disruption_id: Optional disruption ID filter
        status_filter: Optional status filter (pending/approved/rejected)
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of scenarios
    """
    query = db.query(Scenario)

    if disruption_id:
        query = query.filter(Scenario.disruption_id == disruption_id)

    if status_filter:
        query = query.filter(Scenario.status == status_filter)

    scenarios = (
        query.order_by(Scenario.created_at.desc()).offset(offset).limit(limit).all()
    )

    return [
        ScenarioResponse(
            scenario_id=s.scenario_id,
            disruption_id=s.disruption_id,
            order_id=s.order_id,
            action_type=s.action_type,
            plan_json=json.loads(s.plan_json),
            score_json=json.loads(s.score_json),
            status=s.status,
            used_llm=getattr(s, 'used_llm', False) or False,
            llm_rationale=getattr(s, 'llm_rationale', None),
            created_at=s.created_at,
        )
        for s in scenarios
    ]


@router.get("/pending", response_model=list[ScenarioPendingResponse])
def list_pending_scenarios(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ScenarioPendingResponse]:
    """
    List pending scenarios with joined disruption and order info.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of pending scenarios with context
    """
    scenarios = (
        db.query(Scenario, Disruption, Order)
        .join(Disruption, Scenario.disruption_id == Disruption.id)
        .join(Order, Scenario.order_id == Order.order_id)
        .filter(Scenario.status == "pending")
        .order_by(Scenario.created_at.desc())
        .all()
    )

    return [
        ScenarioPendingResponse(
            scenario_id=s.scenario_id,
            disruption_id=s.disruption_id,
            order_id=s.order_id,
            action_type=s.action_type,
            plan_json=json.loads(s.plan_json),
            score_json=json.loads(s.score_json),
            status=s.status,
            used_llm=getattr(s, 'used_llm', False) or False,
            llm_rationale=getattr(s, 'llm_rationale', None),
            created_at=s.created_at,
            disruption_type=d.type,
            disruption_severity=d.severity,
            order_priority=o.priority,
            order_dc=o.dc,
        )
        for s, d, o in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScenarioResponse:
    """
    Get a specific scenario by ID.

    Args:
        scenario_id: Scenario ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Scenario details

    Raises:
        HTTPException: If scenario not found
    """
    scenario = (
        db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    )

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Scenario {scenario_id} not found",
                }
            },
        )

    return ScenarioResponse(
        scenario_id=scenario.scenario_id,
        disruption_id=scenario.disruption_id,
        order_id=scenario.order_id,
        action_type=scenario.action_type,
        plan_json=json.loads(scenario.plan_json),
        score_json=json.loads(scenario.score_json),
        status=scenario.status,
        created_at=scenario.created_at,
    )


@router.post("/{scenario_id}/approve", response_model=ApprovalResponse)
def approve_scenario(
    scenario_id: str,
    request: ApproveRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("warehouse_manager"))],
) -> ApprovalResponse:
    """
    Approve a scenario and apply changes to operational database.
    This is the REAL execution gating - changes only happen here.

    Args:
        scenario_id: Scenario ID to approve
        request: Approval request with note
        db: Database session
        current_user: Current authenticated warehouse manager

    Returns:
        Approval response with applied changes

    Raises:
        HTTPException: If scenario not found, not pending, or constraints violated
    """
    # Check if scenario exists and is pending
    scenario = (
        db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    )

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Scenario {scenario_id} not found",
                }
            },
        )

    if scenario.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_PENDING",
                    "message": f"Scenario {scenario_id} is {scenario.status}, cannot approve",
                    "meta": {"current_status": scenario.status},
                }
            },
        )

    # Apply scenario changes
    try:
        changes_summary = apply_scenario(
            db, scenario_id, current_user.user_id, request.note
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "EXECUTION_FAILED",
                    "message": str(e),
                }
            },
        )

    return ApprovalResponse(
        scenario_id=scenario_id,
        status="approved",
        applied_changes=changes_summary,
        decision_log_id=changes_summary["decision_log_id"],
    )


@router.post("/{scenario_id}/reject", response_model=RejectionResponse)
def reject_scenario(
    scenario_id: str,
    request: ApproveRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("warehouse_manager"))],
) -> RejectionResponse:
    """
    Reject a scenario without applying changes.

    Args:
        scenario_id: Scenario ID to reject
        request: Rejection request with note
        db: Database session
        current_user: Current authenticated warehouse manager

    Returns:
        Rejection response

    Raises:
        HTTPException: If scenario not found or not pending
    """
    scenario = (
        db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    )

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Scenario {scenario_id} not found",
                }
            },
        )

    if scenario.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_PENDING",
                    "message": f"Scenario {scenario_id} is {scenario.status}, cannot reject",
                    "meta": {"current_status": scenario.status},
                }
            },
        )

    # Update scenario status
    scenario.status = "rejected"

    # Create decision log
    log_id = str(uuid.uuid4())
    plan = json.loads(scenario.plan_json)

    decision_log = DecisionLog(
        log_id=log_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_run_id=plan.get("pipeline_run_id", "manual"),
        agent_name="HumanRejection",
        input_summary=f"Reject scenario {scenario_id} ({scenario.action_type}) for order {scenario.order_id}",
        output_summary=f"Scenario rejected by {current_user.username}",
        confidence_score=1.0,
        rationale=f"Human rejection by {current_user.user_id}",
        human_decision="rejected",
        approver_id=current_user.user_id,
        approver_note=request.note,
        override_value=None,
    )

    db.add(decision_log)
    db.commit()

    return RejectionResponse(
        scenario_id=scenario_id,
        status="rejected",
        decision_log_id=log_id,
    )


@router.post("/{scenario_id}/edit", response_model=EditResponse)
def edit_scenario(
    scenario_id: str,
    request: EditScenarioRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role("warehouse_manager"))],
) -> EditResponse:
    """
    Edit a scenario's plan and re-score it.

    Args:
        scenario_id: Scenario ID to edit
        request: Edit request with override plan and note
        db: Database session
        current_user: Current authenticated warehouse manager

    Returns:
        Edit response with updated scenario

    Raises:
        HTTPException: If scenario not found
    """
    scenario = (
        db.query(Scenario).filter(Scenario.scenario_id == scenario_id).first()
    )

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Scenario {scenario_id} not found",
                }
            },
        )

    # Update plan
    old_plan = json.loads(scenario.plan_json)
    new_plan = {**old_plan, **request.override_plan_json}
    scenario.plan_json = json.dumps(new_plan)

    # Re-score scenario
    try:
        from app.agents.scoring import score_scenario

        order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
        if not order:
            raise ValueError(f"Order {scenario.order_id} not found")

        # Get order line count
        from app.db.models import OrderLine
        order_line_count = (
            db.query(OrderLine).filter(OrderLine.order_id == scenario.order_id).count()
        )

        new_score = score_scenario(
            action_type=scenario.action_type,
            order_priority=order.priority,
            plan=new_plan,
            order_line_count=order_line_count,
        )
        scenario.score_json = json.dumps(new_score)
    except Exception as e:
        # If scoring fails, keep old score but log warning
        print(f"Warning: Could not re-score scenario: {e}")
        new_score = json.loads(scenario.score_json)

    # Ensure status is pending after edit
    scenario.status = "pending"

    # Create decision log
    log_id = str(uuid.uuid4())
    decision_log = DecisionLog(
        log_id=log_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_run_id=old_plan.get("pipeline_run_id", "manual"),
        agent_name="HumanEdit",
        input_summary=f"Edit scenario {scenario_id} ({scenario.action_type}) for order {scenario.order_id}",
        output_summary=f"Plan updated by {current_user.username}",
        confidence_score=1.0,
        rationale=f"Human edit by {current_user.user_id}",
        human_decision="edited",
        approver_id=current_user.user_id,
        approver_note=request.note,
        override_value=json.dumps(request.override_plan_json),
    )

    db.add(decision_log)
    db.commit()

    return EditResponse(
        scenario_id=scenario_id,
        status=scenario.status,
        updated_plan_json=new_plan,
        updated_score_json=new_score,
        decision_log_id=log_id,
    )
