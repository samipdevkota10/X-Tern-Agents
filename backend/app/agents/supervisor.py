"""
Supervisor node for orchestrating the multi-agent pipeline.

Now uses LLM-driven routing as the default, with deterministic guardrails
for prerequisites and loop control.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from app.agents.bedrock_explain import generate_explanation
from app.agents.llm_router import decide_next_step, should_use_llm_routing
from app.agents.routing_policy import (
    override_step_if_needed,
    should_force_review,
    get_safe_fallback_step,
)
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import update_pipeline_run, write_decision_log

logger = logging.getLogger(__name__)

# Max pipeline steps from env (default 20)
MAX_PIPELINE_STEPS = int(os.getenv("MAX_PIPELINE_STEPS", "20"))


def log_agent_step(
    pipeline_run_id: str,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    confidence_score: float,
    rationale: str,
) -> None:
    """Helper to log agent decision step."""
    entry = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": pipeline_run_id,
        "agent_name": agent_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "confidence_score": confidence_score,
        "rationale": rationale,
        "human_decision": "pending",
        "approver_id": None,
        "approver_note": None,
        "override_value": None,
    }
    write_decision_log.invoke({"entry": entry})


def supervisor_node(state: PipelineState) -> dict[str, Any]:
    """
    Supervisor node that routes between agents and finalizes results.
    
    Uses LLM-driven routing by default with deterministic guardrails.
    
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
    
    write_status_safe(pipeline_run_id, "supervisor", "routing", {"step": current_step})
    
    # Check for max steps exceeded (loop protection)
    if step_count >= max_steps:
        logger.warning(f"Pipeline {pipeline_run_id} exceeded max steps ({max_steps})")
        write_status_safe(pipeline_run_id, "supervisor", "max_steps_exceeded")
        
        # Force finalize with review flag
        finalize_result = _finalize_pipeline(state, needs_review=True)
        return {
            **finalize_result,
            "step": "END",
            "step_count": step_count,
            "needs_review": True,
            "early_exit_reason": "max_steps_exceeded",
            "routing_trace": routing_trace,
        }
    
    # Check for errors
    if current_step == "error":
        error_msg = state.get("error", "Unknown error")
        write_status_safe(pipeline_run_id, "supervisor", "failed", {"error": error_msg})
        
        # Update pipeline run with error
        update_pipeline_run.invoke({
            "pipeline_run_id": pipeline_run_id,
            "updates": {
                "status": "failed",
                "error_message": error_msg,
                "completed_at": True,
            },
        })
        
        return {"step": "END", "step_count": step_count}
    
    # Finalization step - process immediately
    if current_step == "finalize":
        needs_review, review_reason = should_force_review(state)
        finalize_result = _finalize_pipeline(state, needs_review=needs_review)
        return {
            **finalize_result,
            "step": "END",
            "step_count": step_count,
            "needs_review": needs_review,
            "early_exit_reason": review_reason,
            "routing_trace": routing_trace,
        }
    
    # Track scenario generator retries
    if current_step == "scenario_generator":
        scenarios = state.get("scenarios", [])
        if not scenarios or len(scenarios) == 0:
            scenario_retry_count += 1
    
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
    
    # Add to routing trace (keep entries small)
    routing_trace.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": current_step,
        "llm_next": llm_next_step,
        "final": final_next_step,
        "override": override_reason,
        "confidence": llm_confidence,
        "reason": llm_reason[:100] if llm_reason else None,
    })
    
    # Check if we should finalize
    if final_next_step == "finalize":
        needs_review, review_reason = should_force_review(state)
        finalize_result = _finalize_pipeline(state, needs_review=needs_review)
        return {
            **finalize_result,
            "step": "END",
            "step_count": step_count,
            "needs_review": needs_review,
            "early_exit_reason": review_reason or override_reason,
            "routing_trace": routing_trace,
            "scenario_retry_count": scenario_retry_count,
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


def _finalize_pipeline(state: PipelineState, needs_review: bool = False) -> dict[str, Any]:
    """
    Finalize the pipeline with unified recommendations.
    
    Robust to early-exit and missing artifacts - will generate valid output
    even with partial data.
    
    Args:
        state: Current pipeline state
        needs_review: Flag indicating human review is required
        
    Returns:
        State updates with final summary
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal") or {}
    scored_scenarios = state.get("scores") or []
    scenarios = state.get("scenarios") or []
    routing_trace = state.get("routing_trace", [])
    early_exit_reason = state.get("early_exit_reason")
    
    write_status_safe(pipeline_run_id, "supervisor", "finalizing")
    
    try:
        # Extract impacted orders count safely
        impacted_orders = (
            signal.get("impacted_orders", []) or 
            signal.get("impacted_order_ids", []) or 
            []
        )
        impacted_orders_count = len(impacted_orders) if impacted_orders else 0
        
        # Build recommendations: best scenario per order (if we have scores)
        recommended_actions = []
        approval_queue_count = 0
        
        if scored_scenarios:
            order_scenarios = {}
            for scenario in scored_scenarios:
                order_id = scenario.get("order_id")
                if not order_id:
                    continue
                if order_id not in order_scenarios:
                    order_scenarios[order_id] = []
                order_scenarios[order_id].append(scenario)
            
            for order_id, order_scens in order_scenarios.items():
                # Pick scenario with lowest overall_score
                scored = [s for s in order_scens if s.get("score_json")]
                if scored:
                    best = min(
                        scored, 
                        key=lambda s: s.get("score_json", {}).get("overall_score", float('inf'))
                    )
                    score_json = best.get("score_json", {})
                    recommended_actions.append({
                        "order_id": order_id,
                        "scenario_id": best.get("scenario_id"),
                        "action_type": best.get("action_type"),
                        "overall_score": score_json.get("overall_score"),
                        "cost_impact_usd": score_json.get("cost_impact_usd", 0),
                        "sla_risk": score_json.get("sla_risk", 0),
                        "needs_approval": score_json.get("needs_approval", False),
                    })
                    if score_json.get("needs_approval"):
                        approval_queue_count += 1
        
        # Calculate KPIs (handle empty/missing data)
        total_cost = 0.0
        avg_sla_risk = 0.0
        total_labor = 0
        
        if scored_scenarios:
            for s in scored_scenarios:
                score_json = s.get("score_json") or {}
                total_cost += score_json.get("cost_impact_usd", 0)
                avg_sla_risk += score_json.get("sla_risk", 0)
                total_labor += score_json.get("labor_impact_minutes", 0)
            
            if len(scored_scenarios) > 0:
                avg_sla_risk = avg_sla_risk / len(scored_scenarios)
        
        # Build final summary
        final_summary = {
            "pipeline_run_id": pipeline_run_id,
            "disruption_id": signal.get("disruption_id") or state.get("disruption_id"),
            "impacted_orders_count": impacted_orders_count,
            "scenarios_count": len(scored_scenarios) or len(scenarios),
            "recommended_actions": recommended_actions,
            "approval_queue_count": approval_queue_count,
            "needs_review": needs_review,
            "early_exit_reason": early_exit_reason,
            "kpis": {
                "estimated_cost": round(total_cost, 2),
                "estimated_sla_risk_avg": round(avg_sla_risk, 3),
                "estimated_labor_minutes": total_labor,
            },
        }
        
        # Add routing trace metadata if available
        if routing_trace:
            final_summary["routing_steps"] = len(routing_trace)
            final_summary["routing_summary"] = [
                {"from": t.get("from"), "to": t.get("final")}
                for t in routing_trace[-5:]  # Last 5 steps
            ]
        
        # Generate explanation (optional Bedrock)
        try:
            if needs_review:
                # Custom explanation for review-needed cases
                final_summary["explanation"] = (
                    f"Pipeline completed with review required. "
                    f"Reason: {early_exit_reason or 'unknown'}. "
                    f"Scenarios: {len(scenarios)}, Scored: {len(scored_scenarios)}."
                )
            else:
                explanation = generate_explanation(final_summary)
                final_summary["explanation"] = explanation
        except Exception as e:
            final_summary["explanation"] = f"Explanation generation failed: {str(e)}"
        
        # Determine final status
        final_status = "needs_review" if needs_review else "done"
        
        # Update pipeline run
        update_pipeline_run.invoke({
            "pipeline_run_id": pipeline_run_id,
            "updates": {
                "status": final_status,
                "final_summary_json": final_summary,
                "completed_at": True,
            },
        })
        
        # Log supervisor decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="Supervisor",
            input_summary=f"{len(scored_scenarios)} scored scenarios, {len(scenarios)} total",
            output_summary=f"Finalized {len(recommended_actions)} recommendations, {approval_queue_count} need approval, review={needs_review}",
            confidence_score=0.95 if not needs_review else 0.5,
            rationale=f"Compiled recommendations. Early exit: {early_exit_reason}" if early_exit_reason else "Compiled best scenario per order",
        )
        
        write_status_safe(
            pipeline_run_id,
            "supervisor",
            "completed",
            {
                "recommendations": len(recommended_actions),
                "approval_queue": approval_queue_count,
                "needs_review": needs_review,
            },
        )
        
        return {
            "final_summary": final_summary,
        }
        
    except Exception as e:
        logger.exception(f"Finalization failed for {pipeline_run_id}")
        write_status_safe(pipeline_run_id, "supervisor", "failed", {"error": str(e)})
        return {
            "error": f"Finalization failed: {str(e)}",
            "step": "error",
        }


def route_supervisor(
    state: PipelineState,
) -> Literal["signal_intake", "constraint_builder", "scenario_generator", "tradeoff_scoring", "END"]:
    """
    Router function for supervisor conditional edges.
    
    Now simply returns the step computed by supervisor_node.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Next node name
    """
    # Use the step field set by supervisor_node
    step = state.get("step", "END")
    
    if step == "signal_intake":
        return "signal_intake"
    elif step == "constraint_builder":
        return "constraint_builder"
    elif step == "scenario_generator":
        return "scenario_generator"
    elif step == "tradeoff_scoring":
        return "tradeoff_scoring"
    else:
        return "END"
