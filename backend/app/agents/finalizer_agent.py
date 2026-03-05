"""
Finalizer Agent - Compile final recommendations and complete the pipeline.

Single responsibility: Generate unified recommendations, calculate KPIs,
and mark the pipeline as complete.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.bedrock_explain import generate_explanation
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import update_pipeline_run, write_decision_log

logger = logging.getLogger(__name__)


def finalizer_node(state: PipelineState) -> dict[str, Any]:
    """
    Finalizer node that compiles final recommendations and completes the pipeline.
    
    Single responsibility: Generate summary, calculate KPIs, mark complete.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with final summary
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal") or {}
    scored_scenarios = state.get("scores") or []
    scenarios = state.get("scenarios") or []
    routing_trace = state.get("routing_trace", [])
    early_exit_reason = state.get("early_exit_reason")
    needs_review = state.get("needs_review", False)
    
    write_status_safe(pipeline_run_id, "finalizer", "finalizing")
    
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
            order_scenarios: dict[str, list[dict[str, Any]]] = {}
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
        final_summary: dict[str, Any] = {
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
            final_summary["routing_trace"] = routing_trace  # Full trace for frontend
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
        
        # Log finalizer decision
        _log_finalizer_step(
            pipeline_run_id=pipeline_run_id,
            scenarios_count=len(scored_scenarios) or len(scenarios),
            recommendations_count=len(recommended_actions),
            approval_queue_count=approval_queue_count,
            needs_review=needs_review,
            early_exit_reason=early_exit_reason,
        )
        
        write_status_safe(
            pipeline_run_id,
            "finalizer",
            "completed",
            {
                "recommendations": len(recommended_actions),
                "approval_queue": approval_queue_count,
                "needs_review": needs_review,
            },
        )
        
        return {
            "final_summary": final_summary,
            "step": "END",
        }
        
    except Exception as e:
        logger.exception(f"Finalization failed for {pipeline_run_id}")
        write_status_safe(pipeline_run_id, "finalizer", "failed", {"error": str(e)})
        return {
            "error": f"Finalization failed: {str(e)}",
            "step": "error",
        }


def _log_finalizer_step(
    pipeline_run_id: str,
    scenarios_count: int,
    recommendations_count: int,
    approval_queue_count: int,
    needs_review: bool,
    early_exit_reason: str | None,
) -> None:
    """Log finalizer step to decision log."""
    confidence = 0.95 if not needs_review else 0.5
    
    entry = {
        "log_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_run_id": pipeline_run_id,
        "agent_name": "Finalizer",
        "input_summary": f"{scenarios_count} scenarios to finalize",
        "output_summary": f"Generated {recommendations_count} recommendations, {approval_queue_count} need approval",
        "confidence_score": confidence,
        "rationale": f"Compiled best scenario per order. Early exit: {early_exit_reason}" if early_exit_reason else "Compiled recommendations successfully",
        "human_decision": "pending",
        "approver_id": None,
        "approver_note": None,
        "override_value": None,
    }
    write_decision_log.invoke({"entry": entry})
