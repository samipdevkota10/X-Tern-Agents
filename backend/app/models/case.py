"""
Case models for the application.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class Decision(BaseModel):
    """Decision log entry model."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    decision: str
    made_by: str
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False


class CaseCreate(BaseModel):
    """Request model for creating a case."""
    
    title: str
    description: str
    priority: str = "normal"
    assigned_to: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Case(BaseModel):
    """Case model."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    priority: str = "normal"
    status: str = "open"
    assigned_to: Optional[str] = None
    decisions: list[Decision] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CaseListResponse(BaseModel):
    """Response model for listing cases."""
    
    cases: list[Case]
    total: int
    page: int = 1
    page_size: int = 10


class DecisionCreate(BaseModel):
    """Request model for creating a decision."""
    
    decision: str
    made_by: str
    reason: Optional[str] = None
    approved: bool = False
