"""
Routing Policy - Deterministic guardrails for LLM-driven routing.

This module enforces hard prerequisites and loop-control rules that
must be respected regardless of LLM suggestions.
"""
import os
from typing import Optional

from app.agents.state import PipelineState


# Allowed steps for validation
ALLOWED_STEPS = {
    "signal_intake",
    "constraint_builder",
    "scenario_generator",
    "tradeoff_scoring",
    "finalize",
}

# Maximum retries for scenario generation before forcing finalize
MAX_SCENARIO_RETRIES = int(os.getenv("MAX_SCENARIO_RETRIES", "3"))

# Maximum times same step can repeat before loop detection triggers
MAX_SAME_STEP_REPEATS = int(os.getenv("MAX_SAME_STEP_REPEATS", "3"))


def compute_prereq_violations(
    state: PipelineState,
    proposed_step: str,
) -> list[str]:
    """
    Check if proposed step violates any prerequisites.
    
    Args:
        state: Current pipeline state
        proposed_step: The step LLM wants to execute
        
    Returns:
        List of violation descriptions (empty if valid)
    """
    violations = []
    
    # Get state data with safe defaults
    signal = state.get("signal")
    constraints = state.get("constraints")
    scenarios = state.get("scenarios", [])
    
    # Check prerequisites based on proposed step
    if proposed_step == "tradeoff_scoring":
        # Tradeoff scoring requires scenarios to exist
        if not scenarios or len(scenarios) == 0:
            violations.append("tradeoff_scoring requires scenarios; none exist")
    
    elif proposed_step == "scenario_generator":
        # Scenario generator requires constraints
        if not constraints or len(constraints) == 0:
            violations.append("scenario_generator requires constraints; none exist")
    
    elif proposed_step == "constraint_builder":
        # Constraint builder requires signal with impacted orders
        if not signal:
            violations.append("constraint_builder requires signal; none exists")
        elif not signal.get("impacted_order_ids") and not signal.get("impacted_orders"):
            violations.append("constraint_builder requires impacted orders in signal; none found")
    
    return violations


def override_step_if_needed(
    state: PipelineState,
    proposed_step: str,
) -> tuple[str, Optional[str]]:
    """
    Override the proposed step if prerequisites are violated or loop control triggers.
    
    Args:
        state: Current pipeline state
        proposed_step: The step LLM wants to execute
        
    Returns:
        Tuple of (actual_step, override_reason or None)
    """
    # Get state data with safe defaults
    signal = state.get("signal")
    constraints = state.get("constraints")
    scenarios = state.get("scenarios", [])
    scenario_retry_count = state.get("scenario_retry_count", 0)
    routing_trace = state.get("routing_trace", [])
    
    # Validate proposed step is allowed
    if proposed_step not in ALLOWED_STEPS:
        # Default to finalize for invalid steps
        return "finalize", f"invalid_step_{proposed_step}"
    
    # Check for prerequisite violations and override
    violations = compute_prereq_violations(state, proposed_step)
    
    if violations:
        # Determine correct override based on what's missing
        if proposed_step == "tradeoff_scoring" and not scenarios:
            # Need scenarios first
            if not constraints:
                if not signal:
                    return "signal_intake", "prereq_missing_signal"
                return "constraint_builder", "prereq_missing_constraints"
            return "scenario_generator", "prereq_missing_scenarios"
        
        elif proposed_step == "scenario_generator" and not constraints:
            if not signal:
                return "signal_intake", "prereq_missing_signal"
            return "constraint_builder", "prereq_missing_constraints"
        
        elif proposed_step == "constraint_builder" and not signal:
            return "signal_intake", "prereq_missing_signal"
    
    # Loop control: Check if scenario_generator has been retried too many times
    if proposed_step == "scenario_generator":
        if scenario_retry_count >= MAX_SCENARIO_RETRIES:
            # Exhausted retries with no scenarios
            return "finalize", f"scenario_retries_exhausted_{scenario_retry_count}"
    
    # Loop control: Check if same step is being repeated too many times
    recent_steps = [
        entry.get("final_next_step") 
        for entry in routing_trace[-MAX_SAME_STEP_REPEATS:]
    ]
    if len(recent_steps) >= MAX_SAME_STEP_REPEATS and all(s == proposed_step for s in recent_steps):
        return "finalize", f"loop_detected_repeated_{proposed_step}"
    
    # No override needed
    return proposed_step, None


def should_force_review(state: PipelineState) -> tuple[bool, Optional[str]]:
    """
    Determine if the pipeline state requires human review.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Tuple of (needs_review, reason or None)
    """
    scenarios = state.get("scenarios", [])
    scores = state.get("scores", [])
    early_exit_reason = state.get("early_exit_reason")
    scenario_retry_count = state.get("scenario_retry_count", 0)
    
    # Force review if early exit was triggered
    if early_exit_reason:
        return True, f"early_exit: {early_exit_reason}"
    
    # Force review if scenario generation failed repeatedly
    if scenario_retry_count >= MAX_SCENARIO_RETRIES and not scenarios:
        return True, "no_scenarios_after_max_retries"
    
    # Force review if there are scenarios but no scores
    if scenarios and not scores:
        return True, "unscored_scenarios"
    
    return False, None


def get_safe_fallback_step(state: PipelineState) -> str:
    """
    Get a safe fallback step based on current state.
    
    This is used when LLM fails to provide a valid response.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Safe next step name
    """
    signal = state.get("signal")
    constraints = state.get("constraints")
    scenarios = state.get("scenarios", [])
    scores = state.get("scores", [])
    
    # Progressive fallback based on what's available
    if not signal:
        return "signal_intake"
    elif not constraints or len(constraints) == 0:
        return "constraint_builder"
    elif not scenarios or len(scenarios) == 0:
        return "scenario_generator"
    elif not scores or len(scores) == 0:
        return "tradeoff_scoring"
    else:
        return "finalize"
