"""
Router Agent - LLM-driven routing for multi-agent pipeline.

Single responsibility: Decide the next step in the pipeline using LLM with
deterministic guardrails for prerequisites and loop control.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.agents.llm_router import decide_next_step, should_use_llm_routing
from app.agents.routing_policy import (
    override_step_if_needed,
    should_force_review,
)
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tool_router import write_decision_log

logger = logging.getLogger(__name__)

# Max pipeline steps from env (default 20)
MAX_PIPELINE_STEPS = int(os.getenv("MAX_PIPELINE_STEPS", "20"))


def router_node(state: PipelineState) -> dict[str, Any]:
    """
    Router node that decides the next step in the pipeline.
    
    Uses LLM-driven routing by default with deterministic guardrails.
    
    Single responsibility: Route to the appropriate agent based on current state.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with routing decision
    """
    pipeline_run_id = state["pipeline_run_id"]
    current_step = state.get("step", "start")
    
    # Initialize routing state fields with safe defaults
    step_count = state.get("step_count", 0) + 1
    routing_trace = list(state.get("routing_trace", []))
    scenario_retry_count = state.get("scenario_retry_count", 0)
    max_steps = state.get("max_steps") or MAX_PIPELINE_STEPS
    
    write_status_safe(pipeline_run_id, "router", "routing", {"step": current_step})
    
    # Check for max steps exceeded (loop protection)
    if step_count >= max_steps:
        logger.warning(
            f"Pipeline {pipeline_run_id} exceeded max steps ({max_steps}). Forcing finalize."
        )
        routing_trace.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "from": current_step,
            "llm_next": None,
            "final": "finalize",
            "override": "max_steps_exceeded",
            "confidence": None,
            "reason": f"Exceeded max steps limit ({max_steps})",
        })
        
        return {
            "step": "finalize",
            "next_step": "finalize",
            "step_count": step_count,
            "routing_trace": routing_trace,
            "scenario_retry_count": scenario_retry_count,
            "early_exit_reason": f"max_steps_exceeded ({max_steps})",
        }
    
    # Handle start state
    if current_step == "start":
        routing_trace.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "from": "start",
            "llm_next": "signal_intake",
            "final": "signal_intake",
            "override": None,
            "confidence": 1.0,
            "reason": "Pipeline initialization",
        })
        
        _log_router_decision(
            pipeline_run_id=pipeline_run_id,
            from_step="start",
            to_step="signal_intake",
            confidence=1.0,
            rationale="Pipeline initialized, starting with signal intake",
        )
        
        return {
            "step": "signal_intake",
            "next_step": "signal_intake",
            "step_count": step_count,
            "routing_trace": routing_trace,
            "scenario_retry_count": scenario_retry_count,
        }
    
    # Determine next step using LLM or deterministic routing
    if should_use_llm_routing():
        # LLM-driven routing (default)
        llm_decision = decide_next_step(state, current_step)
        llm_next_step = llm_decision["next_step"]
        llm_reason = llm_decision.get("reason", "")
        llm_confidence = llm_decision.get("confidence")
        
        # Apply deterministic guardrails
        final_next_step, override_reason = override_step_if_needed(state, llm_next_step)
        
        # Log routing decision
        logger.info(
            f"Routing: {current_step} -> {final_next_step} "
            f"(LLM suggested: {llm_next_step}, override: {override_reason}, "
            f"confidence: {llm_confidence})"
        )
    else:
        # Deterministic routing (emergency fallback)
        llm_next_step = None
        llm_reason = "deterministic_mode"
        llm_confidence = None
        final_next_step = _deterministic_route(current_step, state)
        override_reason = "deterministic_routing_enabled"
    
    # Add to routing trace
    routing_trace.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": current_step,
        "llm_next": llm_next_step,
        "final": final_next_step,
        "override": override_reason,
        "confidence": llm_confidence,
        "reason": llm_reason[:100] if llm_reason else None,
    })
    
    _log_router_decision(
        pipeline_run_id=pipeline_run_id,
        from_step=current_step,
        to_step=final_next_step,
        confidence=llm_confidence or 0.8,
        rationale=f"LLM: {llm_reason[:80]}" if llm_reason else f"Routed {current_step} -> {final_next_step}",
        override=override_reason,
    )
    
    # Check for early exit scenarios
    if final_next_step == "finalize":
        needs_review, review_reason = should_force_review(state)
        return {
            "step": "finalize",
            "next_step": "finalize",
            "step_count": step_count,
            "routing_trace": routing_trace,
            "scenario_retry_count": scenario_retry_count,
            "needs_review": needs_review,
            "early_exit_reason": review_reason or override_reason,
        }
    
    # Return state update with next step
    return {
        "step": final_next_step,
        "next_step": final_next_step,
        "step_count": step_count,
        "routing_trace": routing_trace,
        "scenario_retry_count": scenario_retry_count,
    }


def _deterministic_route(current_step: str, state: PipelineState) -> str:
    """
    Legacy deterministic routing logic.
    
    Only used when USE_DETERMINISTIC_ROUTING=1 is set.
    """
    if current_step == "start":
        return "signal_intake"
    elif current_step == "signal_intake":
        return "constraint_builder"
    elif current_step == "constraint_builder":
        return "scenario_generator"
    elif current_step == "scenario_generator":
        return "tradeoff_scoring"
    elif current_step == "tradeoff_scoring":
        return "finalize"
    else:
        return "finalize"


def _log_router_decision(
    pipeline_run_id: str,
    from_step: str,
    to_step: str,
    confidence: float,
    rationale: str,
    override: str | None = None,
) -> None:
    """Log routing decision to decision log."""
    import uuid
    
    entry = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": pipeline_run_id,
        "agent_name": "Router",
        "input_summary": f"Current step: {from_step}",
        "output_summary": f"Routed to: {to_step}" + (f" (override: {override})" if override else ""),
        "confidence_score": confidence,
        "rationale": rationale,
        "human_decision": "pending",
        "approver_id": None,
        "approver_note": None,
        "override_value": None,
    }
    write_decision_log(entry)


def route_router(state: PipelineState) -> str:
    """
    Router function for conditional edges from router node.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Next node name
    """
    step = state.get("step", "END")
    
    if step == "signal_intake":
        return "signal_intake"
    elif step == "constraint_builder":
        return "constraint_builder"
    elif step == "scenario_generator":
        return "scenario_generator"
    elif step == "tradeoff_scoring":
        return "tradeoff_scoring"
    elif step == "finalize":
        return "finalizer"
    else:
        return "END"
