"""
Disruption CRUD routes.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import DisruptionCreate, DisruptionResponse, DisruptionStatusUpdate
from app.core.deps import get_current_user, get_db
from app.db.models import Disruption, User

router = APIRouter(prefix="/api/disruptions", tags=["disruptions"])


@router.post("", response_model=DisruptionResponse, status_code=status.HTTP_201_CREATED)
def create_disruption(
    request: DisruptionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DisruptionResponse:
    """
    Create a new disruption.

    Args:
        request: Disruption creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created disruption
    """
    disruption_id = str(uuid.uuid4())

    disruption = Disruption(
        id=disruption_id,
        type=request.type,
        severity=request.severity,
        timestamp=datetime.now(timezone.utc),
        details_json=json.dumps(request.details_json),
        status="open",
    )

    db.add(disruption)
    db.commit()
    db.refresh(disruption)

    return DisruptionResponse(
        id=disruption.id,
        type=disruption.type,
        severity=disruption.severity,
        timestamp=disruption.timestamp,
        details_json=json.loads(disruption.details_json),
        status=disruption.status,
    )


@router.get("", response_model=list[DisruptionResponse])
def list_disruptions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Optional[str] = Query(None, alias="status"),
) -> list[DisruptionResponse]:
    """
    List disruptions with optional status filter.

    Args:
        db: Database session
        current_user: Current authenticated user
        status_filter: Optional status filter (open/resolved)

    Returns:
        List of disruptions
    """
    query = db.query(Disruption)

    if status_filter:
        query = query.filter(Disruption.status == status_filter)

    disruptions = query.order_by(Disruption.timestamp.desc()).all()

    return [
        DisruptionResponse(
            id=d.id,
            type=d.type,
            severity=d.severity,
            timestamp=d.timestamp,
            details_json=json.loads(d.details_json),
            status=d.status,
        )
        for d in disruptions
    ]


@router.get("/{disruption_id}", response_model=DisruptionResponse)
def get_disruption(
    disruption_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DisruptionResponse:
    """
    Get a specific disruption by ID.

    Args:
        disruption_id: Disruption ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Disruption details

    Raises:
        HTTPException: If disruption not found
    """
    disruption = db.query(Disruption).filter(Disruption.id == disruption_id).first()

    if not disruption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "DISRUPTION_NOT_FOUND",
                    "message": f"Disruption {disruption_id} not found",
                }
            },
        )

    return DisruptionResponse(
        id=disruption.id,
        type=disruption.type,
        severity=disruption.severity,
        timestamp=disruption.timestamp,
        details_json=json.loads(disruption.details_json),
        status=disruption.status,
    )


@router.patch("/{disruption_id}", response_model=DisruptionResponse)
def update_disruption_status(
    disruption_id: str,
    request: DisruptionStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DisruptionResponse:
    """
    Update a disruption's status (open/resolved).
    """
    disruption = db.query(Disruption).filter(Disruption.id == disruption_id).first()

    if not disruption:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "DISRUPTION_NOT_FOUND",
                    "message": f"Disruption {disruption_id} not found",
                }
            },
        )

    disruption.status = request.status
    db.commit()
    db.refresh(disruption)

    return DisruptionResponse(
        id=disruption.id,
        type=disruption.type,
        severity=disruption.severity,
        timestamp=disruption.timestamp,
        details_json=json.loads(disruption.details_json),
        status=disruption.status,
    )
