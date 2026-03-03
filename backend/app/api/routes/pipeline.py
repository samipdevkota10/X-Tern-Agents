"""
Pipeline execution routes.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import PipelineRunRequest, PipelineRunResponse, PipelineStatusResponse
from app.core.deps import get_current_user, get_db
from app.db.models import Disruption, PipelineRun, User
from app.services.pipeline_runner import run_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_pipeline_run(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PipelineRunResponse:
    """
    Start a new pipeline run for a disruption.
    Pipeline executes in background and updates status.

    Args:
        request: Pipeline run request
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user

    Returns:
        Pipeline run ID

    Raises:
        HTTPException: If disruption not found
    """
    # Verify disruption exists
    disruption = (
        db.query(Disruption).filter(Disruption.id == request.disruption_id).first()
    )

    if not disruption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "DISRUPTION_NOT_FOUND",
                    "message": f"Disruption {request.disruption_id} not found",
                }
            },
        )

    # Create pipeline run record
    pipeline_run_id = str(uuid.uuid4())

    pipeline_run = PipelineRun(
        pipeline_run_id=pipeline_run_id,
        disruption_id=request.disruption_id,
        status="queued",
        current_step=None,
        progress=0.0,
        started_at=datetime.now(timezone.utc),
    )

    db.add(pipeline_run)
    db.commit()

    # Start pipeline in background
    # Note: We create a new session in the background task to avoid session issues
    background_tasks.add_task(
        _run_pipeline_background,
        pipeline_run_id,
        request.disruption_id,
    )

    return PipelineRunResponse(pipeline_run_id=pipeline_run_id)


def _run_pipeline_background(pipeline_run_id: str, disruption_id: str) -> None:
    """
    Background task wrapper to run pipeline with its own DB session.

    Args:
        pipeline_run_id: Pipeline run ID
        disruption_id: Disruption ID
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_pipeline(db, pipeline_run_id, disruption_id)
    finally:
        db.close()


@router.get("/{pipeline_run_id}/status", response_model=PipelineStatusResponse)
def get_pipeline_status(
    pipeline_run_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PipelineStatusResponse:
    """
    Get status of a pipeline run.

    Args:
        pipeline_run_id: Pipeline run ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Pipeline run status

    Raises:
        HTTPException: If pipeline run not found
    """
    pipeline_run = (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_run_id == pipeline_run_id)
        .first()
    )

    if not pipeline_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PIPELINE_RUN_NOT_FOUND",
                    "message": f"Pipeline run {pipeline_run_id} not found",
                }
            },
        )

    # Parse final summary JSON if present
    final_summary = None
    if pipeline_run.final_summary_json:
        try:
            final_summary = json.loads(pipeline_run.final_summary_json)
        except json.JSONDecodeError:
            pass

    return PipelineStatusResponse(
        pipeline_run_id=pipeline_run.pipeline_run_id,
        disruption_id=pipeline_run.disruption_id,
        status=pipeline_run.status,
        current_step=pipeline_run.current_step,
        progress=pipeline_run.progress,
        started_at=pipeline_run.started_at,
        completed_at=pipeline_run.completed_at,
        final_summary_json=final_summary,
        error_message=pipeline_run.error_message,
    )
