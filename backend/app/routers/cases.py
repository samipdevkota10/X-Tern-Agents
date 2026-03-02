"""
Cases router - CRUD operations for cases.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from app.models.case import (
    Case,
    CaseCreate,
    CaseListResponse,
    Decision,
    DecisionCreate,
)
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# In-memory storage (will be replaced with DynamoDB)
_cases_db: dict[str, Case] = {}


@router.post("", response_model=Case, status_code=status.HTTP_201_CREATED)
async def create_case(case_data: CaseCreate) -> Case:
    """
    Create a new case.
    """
    case = Case(**case_data.model_dump())
    _cases_db[case.id] = case
    logger.info("Case created", case_id=case.id, title=case.title)
    return case


@router.get("", response_model=CaseListResponse)
async def list_cases(
    page: int = 1,
    page_size: int = 10,
    status_filter: Optional[str] = None,
) -> CaseListResponse:
    """
    List all cases with optional filtering.
    """
    cases = list(_cases_db.values())
    
    if status_filter:
        cases = [c for c in cases if c.status == status_filter]
    
    total = len(cases)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_cases = cases[start:end]
    
    return CaseListResponse(
        cases=paginated_cases,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=Case)
async def get_case(case_id: str) -> Case:
    """
    Get a specific case by ID.
    """
    case = _cases_db.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with id {case_id} not found",
        )
    return case


@router.post("/{case_id}/decisions", response_model=Case)
async def append_decision(case_id: str, decision_data: DecisionCreate) -> Case:
    """
    Append a decision to a case's decision log.
    """
    case = _cases_db.get(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with id {case_id} not found",
        )
    
    decision = Decision(**decision_data.model_dump())
    case.decisions.append(decision)
    case.updated_at = datetime.utcnow()
    
    logger.info(
        "Decision appended to case",
        case_id=case_id,
        decision_id=decision.id,
        made_by=decision.made_by,
    )
    
    return case
