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
    next_step: Optional[str]  # Next step computed by LLM router
    
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
    
    # LLM-driven routing fields (safe defaults)
    step_count: int  # Current step count for loop protection (default: 0)
    max_steps: Optional[int]  # Max steps override (default: use env MAX_PIPELINE_STEPS)
    needs_review: bool  # Flag for human review required (default: False)
    early_exit_reason: Optional[str]  # Reason for early termination
    scenario_retry_count: int  # Retry count for scenario generation (default: 0)
    routing_trace: list  # Trace of routing decisions (list of small dicts)
