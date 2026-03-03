"""
Supervisor node for orchestrating the multi-agent pipeline.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from app.agents.bedrock_explain import generate_explanation
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import update_pipeline_run, write_decision_log


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
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with routing decision
    """
    pipeline_run_id = state["pipeline_run_id"]
    current_step = state.get("step", "start")
    
    write_status_safe(pipeline_run_id, "supervisor", "routing", {"step": current_step})
    
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
        
        return {"step": "END"}
    
    # Finalization step - process immediately
    if current_step == "finalize":
        finalize_result = _finalize_pipeline(state)
        # Return with END step to terminate
        return {**finalize_result, "step": "END"}
    
    # Route to next step based on which agent just completed
    if current_step == "start":
        # Initial routing
        return {"step": "signal_intake"}
    elif current_step == "signal_intake":
        # Signal intake just completed, go to constraint builder
        return {"step": "constraint_builder"}
    elif current_step == "constraint_builder":
        # Constraint builder just completed, go to scenario generator
        return {"step": "scenario_generator"}
    elif current_step == "scenario_generator":
        # Scenario generator just completed, go to tradeoff scoring
        return {"step": "tradeoff_scoring"}
    elif current_step == "tradeoff_scoring":
        # Tradeoff scoring just completed, finalize immediately
        finalize_result = _finalize_pipeline(state)
        # Return with END step to terminate
        return {**finalize_result, "step": "END"}
    
    return {"step": "END"}


def _finalize_pipeline(state: PipelineState) -> dict[str, Any]:
    """
    Finalize the pipeline with unified recommendations.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with final summary
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal", {})
    scored_scenarios = state.get("scores", [])
    
    write_status_safe(pipeline_run_id, "supervisor", "finalizing")
    
    try:
        # Build recommendations: best scenario per order
        order_scenarios = {}
        for scenario in scored_scenarios:
            order_id = scenario["order_id"]
            if order_id not in order_scenarios:
                order_scenarios[order_id] = []
            order_scenarios[order_id].append(scenario)
        
        recommended_actions = []
        for order_id, scenarios in order_scenarios.items():
            # Pick scenario with lowest overall_score
            best = min(scenarios, key=lambda s: s["score_json"]["overall_score"])
            recommended_actions.append({
                "order_id": order_id,
                "scenario_id": best["scenario_id"],
                "action_type": best["action_type"],
                "overall_score": best["score_json"]["overall_score"],
                "cost_impact_usd": best["score_json"]["cost_impact_usd"],
                "sla_risk": best["score_json"]["sla_risk"],
                "needs_approval": best["score_json"]["needs_approval"],
            })
        
        # Calculate KPIs
        approval_queue_count = sum(
            1 for s in scored_scenarios if s["score_json"].get("needs_approval", False)
        )
        
        total_cost = sum(s["score_json"]["cost_impact_usd"] for s in scored_scenarios)
        avg_sla_risk = (
            sum(s["score_json"]["sla_risk"] for s in scored_scenarios) / len(scored_scenarios)
            if scored_scenarios
            else 0.0
        )
        total_labor = sum(s["score_json"]["labor_impact_minutes"] for s in scored_scenarios)
        
        # Build final summary
        final_summary = {
            "pipeline_run_id": pipeline_run_id,
            "disruption_id": signal.get("disruption_id"),
            "impacted_orders_count": len(signal.get("impacted_orders", [])),
            "scenarios_count": len(scored_scenarios),
            "recommended_actions": recommended_actions,
            "approval_queue_count": approval_queue_count,
            "kpis": {
                "estimated_cost": round(total_cost, 2),
                "estimated_sla_risk_avg": round(avg_sla_risk, 3),
                "estimated_labor_minutes": total_labor,
            },
        }
        
        # Generate explanation (optional Bedrock)
        try:
            explanation = generate_explanation(final_summary)
            final_summary["explanation"] = explanation
        except Exception as e:
            final_summary["explanation"] = f"Explanation generation failed: {str(e)}"
        
        # Update pipeline run
        update_pipeline_run.invoke({
            "pipeline_run_id": pipeline_run_id,
            "updates": {
                "status": "done",
                "final_summary_json": final_summary,
                "completed_at": True,
            },
        })
        
        # Log supervisor decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="Supervisor",
            input_summary=f"{len(scored_scenarios)} scored scenarios",
            output_summary=f"Finalized {len(recommended_actions)} recommendations, {approval_queue_count} need approval",
            confidence_score=0.95,
            rationale="Compiled best scenario per order and calculated aggregate KPIs",
        )
        
        write_status_safe(
            pipeline_run_id,
            "supervisor",
            "completed",
            {
                "recommendations": len(recommended_actions),
                "approval_queue": approval_queue_count,
            },
        )
        
        return {
            "final_summary": final_summary,
        }
        
    except Exception as e:
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
    else:
        return "END"
