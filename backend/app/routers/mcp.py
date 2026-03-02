"""
MCP (Model Context Protocol) Tools router.

Provides endpoints for MCP tool operations including:
- read_case_state: Read current state of a case
- write_decision_record: Write a decision to the log
- compute_risk_score: Calculate risk score for a case
"""
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.routers.cases import _cases_db
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


# MCP Tool Request/Response Models

class MCPToolRequest(BaseModel):
    """Base model for MCP tool requests."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(BaseModel):
    """Base model for MCP tool responses."""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: float


class ReadCaseStateRequest(BaseModel):
    """Request model for read_case_state tool."""
    case_id: str


class ReadCaseStateResponse(BaseModel):
    """Response model for read_case_state tool."""
    case_id: str
    exists: bool
    state: Optional[dict[str, Any]] = None


class WriteDecisionRecordRequest(BaseModel):
    """Request model for write_decision_record tool."""
    case_id: str
    decision: str
    made_by: str
    reason: Optional[str] = None
    approved: bool = False


class WriteDecisionRecordResponse(BaseModel):
    """Response model for write_decision_record tool."""
    case_id: str
    decision_id: str
    success: bool


class ComputeRiskScoreRequest(BaseModel):
    """Request model for compute_risk_score tool."""
    case_id: Optional[str] = None
    factors: dict[str, Any] = Field(default_factory=dict)


class ComputeRiskScoreResponse(BaseModel):
    """Response model for compute_risk_score tool."""
    risk_score: float
    risk_level: str
    factors_evaluated: list[str]
    recommendations: list[str]


# MCP Tool Endpoints

@router.get("/tools")
async def list_tools() -> dict[str, Any]:
    """
    List all available MCP tools.
    """
    tools = [
        {
            "name": "read_case_state",
            "description": "Read the current state of a case by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "The unique identifier of the case",
                    }
                },
                "required": ["case_id"],
            },
        },
        {
            "name": "write_decision_record",
            "description": "Write a decision record to a case's decision log",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "The unique identifier of the case",
                    },
                    "decision": {
                        "type": "string",
                        "description": "The decision made",
                    },
                    "made_by": {
                        "type": "string",
                        "description": "Who made the decision",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the decision",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "Whether the decision is approved",
                    },
                },
                "required": ["case_id", "decision", "made_by"],
            },
        },
        {
            "name": "compute_risk_score",
            "description": "Compute a risk score based on provided factors",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Optional case ID to compute risk for",
                    },
                    "factors": {
                        "type": "object",
                        "description": "Risk factors to evaluate",
                    },
                },
                "required": [],
            },
        },
    ]
    
    return {
        "tools": tools,
        "total": len(tools),
    }


@router.post("/tools/read_case_state", response_model=ReadCaseStateResponse)
async def read_case_state(request: ReadCaseStateRequest) -> ReadCaseStateResponse:
    """
    MCP Tool: Read the current state of a case.
    """
    logger.info("MCP Tool: read_case_state", case_id=request.case_id)
    
    case = _cases_db.get(request.case_id)
    
    if case:
        return ReadCaseStateResponse(
            case_id=request.case_id,
            exists=True,
            state=case.model_dump(),
        )
    else:
        return ReadCaseStateResponse(
            case_id=request.case_id,
            exists=False,
            state=None,
        )


@router.post("/tools/write_decision_record", response_model=WriteDecisionRecordResponse)
async def write_decision_record(request: WriteDecisionRecordRequest) -> WriteDecisionRecordResponse:
    """
    MCP Tool: Write a decision record to a case.
    """
    from uuid import uuid4
    from app.models.case import Decision
    
    logger.info(
        "MCP Tool: write_decision_record",
        case_id=request.case_id,
        made_by=request.made_by,
    )
    
    case = _cases_db.get(request.case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with id {request.case_id} not found",
        )
    
    decision = Decision(
        id=str(uuid4()),
        decision=request.decision,
        made_by=request.made_by,
        reason=request.reason,
        approved=request.approved,
        timestamp=datetime.utcnow(),
    )
    
    case.decisions.append(decision)
    case.updated_at = datetime.utcnow()
    
    return WriteDecisionRecordResponse(
        case_id=request.case_id,
        decision_id=decision.id,
        success=True,
    )


@router.post("/tools/compute_risk_score", response_model=ComputeRiskScoreResponse)
async def compute_risk_score(request: ComputeRiskScoreRequest) -> ComputeRiskScoreResponse:
    """
    MCP Tool: Compute a risk score.
    
    This is a dummy implementation that provides a basic risk scoring.
    In production, this would integrate with ML models or rule engines.
    """
    logger.info(
        "MCP Tool: compute_risk_score",
        case_id=request.case_id,
        num_factors=len(request.factors),
    )
    
    # Dummy risk scoring logic
    base_score = 0.5
    factors_evaluated = []
    
    # Evaluate factors
    if "priority" in request.factors:
        priority = request.factors["priority"]
        if priority == "high":
            base_score += 0.2
        elif priority == "low":
            base_score -= 0.2
        factors_evaluated.append("priority")
    
    if "amount" in request.factors:
        amount = request.factors.get("amount", 0)
        if amount > 100000:
            base_score += 0.3
        elif amount > 50000:
            base_score += 0.1
        factors_evaluated.append("amount")
    
    if "history" in request.factors:
        history = request.factors.get("history", {})
        if history.get("previous_issues", 0) > 3:
            base_score += 0.2
        factors_evaluated.append("history")
    
    if "urgency" in request.factors:
        if request.factors["urgency"]:
            base_score += 0.15
        factors_evaluated.append("urgency")
    
    # If case_id provided, factor in case data
    if request.case_id:
        case = _cases_db.get(request.case_id)
        if case:
            if case.priority == "high":
                base_score += 0.1
            if len(case.decisions) == 0:
                base_score += 0.05  # No decisions yet
            factors_evaluated.append("case_data")
    
    # Clamp score between 0 and 1
    risk_score = max(0.0, min(1.0, base_score))
    
    # Determine risk level
    if risk_score >= 0.8:
        risk_level = "critical"
    elif risk_score >= 0.6:
        risk_level = "high"
    elif risk_score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate recommendations
    recommendations = []
    if risk_level in ("critical", "high"):
        recommendations.append("Require manual review before proceeding")
        recommendations.append("Escalate to senior reviewer")
    if risk_level == "medium":
        recommendations.append("Standard review process recommended")
    if not factors_evaluated:
        recommendations.append("Provide more factors for accurate scoring")
    
    return ComputeRiskScoreResponse(
        risk_score=round(risk_score, 3),
        risk_level=risk_level,
        factors_evaluated=factors_evaluated,
        recommendations=recommendations,
    )


@router.post("/tools/execute")
async def execute_tool(request: MCPToolRequest) -> MCPToolResponse:
    """
    Generic endpoint to execute any MCP tool by name.
    """
    import time
    
    start_time = time.time()
    tool_name = request.tool_name
    arguments = request.arguments
    
    logger.info("Executing MCP tool", tool_name=tool_name)
    
    try:
        if tool_name == "read_case_state":
            req = ReadCaseStateRequest(**arguments)
            result = await read_case_state(req)
        elif tool_name == "write_decision_record":
            req = WriteDecisionRecordRequest(**arguments)
            result = await write_decision_record(req)
        elif tool_name == "compute_risk_score":
            req = ComputeRiskScoreRequest(**arguments)
            result = await compute_risk_score(req)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tool: {tool_name}",
            )
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return MCPToolResponse(
            tool_name=tool_name,
            success=True,
            result=result.model_dump(),
            execution_time_ms=round(execution_time_ms, 2),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        logger.error("MCP tool execution failed", tool_name=tool_name, error=str(e))
        return MCPToolResponse(
            tool_name=tool_name,
            success=False,
            result=None,
            error=str(e),
            execution_time_ms=round(execution_time_ms, 2),
        )
