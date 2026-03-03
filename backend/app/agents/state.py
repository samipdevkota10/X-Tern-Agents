"""
Typed state definition for LangGraph multi-agent pipeline.
"""
from typing import Any, Optional, TypedDict


class PipelineState(TypedDict, total=False):
    """
    State passed through the LangGraph pipeline.
    
    Fields are progressively populated by each agent node.
    """
    
    # Pipeline metadata
    pipeline_run_id: str
    disruption_id: str
    step: str  # Current step for supervisor routing
    
    # Signal Intake Agent output
    signal: Optional[dict[str, Any]]  # Normalized incident with impacted_order_ids
    
    # Constraint Builder Agent output
    constraints: Optional[dict[str, Any]]  # Inventory, capacity, substitutions, etc.
    
    # Scenario Generator Agent output
    scenarios: Optional[list[dict[str, Any]]]  # Generated scenarios with plan_json
    
    # Tradeoff Scoring Agent output
    scores: Optional[list[dict[str, Any]]]  # Scenarios with score_json populated
    
    # Final output
    final_summary: Optional[dict[str, Any]]  # Unified recommendation JSON
    
    # Error tracking
    error: Optional[str]
