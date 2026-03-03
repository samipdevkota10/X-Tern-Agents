"""
Audit log routes for decision tracking.
"""
import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import DecisionLogResponse
from app.core.deps import get_current_user, get_db
from app.db.models import DecisionLog, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[DecisionLogResponse])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    pipeline_run_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    human_decision: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[DecisionLogResponse]:
    """
    List decision logs with optional filters and pagination.

    Args:
        db: Database session
        current_user: Current authenticated user
        pipeline_run_id: Optional pipeline run ID filter
        agent_name: Optional agent name filter
        human_decision: Optional human decision filter (approved/rejected/edited/pending)
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of decision logs ordered by timestamp descending
    """
    query = db.query(DecisionLog)

    if pipeline_run_id:
        query = query.filter(DecisionLog.pipeline_run_id == pipeline_run_id)

    if agent_name:
        query = query.filter(DecisionLog.agent_name == agent_name)

    if human_decision:
        query = query.filter(DecisionLog.human_decision == human_decision)

    logs = query.order_by(DecisionLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
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
        for log in logs
    ]
