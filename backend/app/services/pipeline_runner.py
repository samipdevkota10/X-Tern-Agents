"""
Pipeline runner service for executing LangGraph multi-agent pipeline.
"""
import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import DecisionLog, PipelineRun


def run_pipeline(db: Session, pipeline_run_id: str, disruption_id: str) -> None:
    """
    Run the LangGraph multi-agent pipeline for a disruption.
    Updates pipeline_runs table with status, progress, and results.

    Args:
        db: Database session
        pipeline_run_id: Pipeline run ID
        disruption_id: Disruption ID to process

    Note:
        This function catches all exceptions and updates pipeline status accordingly.
        It should be run in a background task.
    """
    try:
        # Update status to running
        pipeline_run = (
            db.query(PipelineRun)
            .filter(PipelineRun.pipeline_run_id == pipeline_run_id)
            .first()
        )

        if not pipeline_run:
            raise ValueError(f"Pipeline run {pipeline_run_id} not found")

        pipeline_run.status = "running"
        pipeline_run.current_step = "initializing"
        pipeline_run.progress = 0.0
        db.commit()

        # Import graph builder (lazy import to avoid circular dependencies)
        from app.agents.graph import build_graph
        from app.agents.state import PipelineState

        # Build graph
        pipeline_run.current_step = "building_graph"
        pipeline_run.progress = 0.1
        db.commit()

        graph = build_graph()

        # Prepare initial state with LLM routing fields initialized
        initial_state: PipelineState = {
            "pipeline_run_id": pipeline_run_id,
            "disruption_id": disruption_id,
            "step": "start",
            # LLM routing fields with safe defaults
            "step_count": 0,
            "max_steps": None,  # Uses MAX_PIPELINE_STEPS env default
            "needs_review": False,
            "early_exit_reason": None,
            "scenario_retry_count": 0,
            "routing_trace": [],
        }

        # Execute graph
        pipeline_run.current_step = "executing"
        pipeline_run.progress = 0.2
        db.commit()

        final_state = graph.invoke(initial_state)

        # Extract final summary
        signal = final_state.get("signal", {})
        scenarios = final_state.get("scenarios", [])
        final_summary_from_state = final_state.get("final_summary", {})
        
        # Get LLM routing metadata
        needs_review = final_state.get("needs_review", False)
        early_exit_reason = final_state.get("early_exit_reason")
        routing_trace = final_state.get("routing_trace", [])
        step_count = final_state.get("step_count", 0)
        
        final_summary = {
            "disruption_id": disruption_id,
            "impacted_orders_count": len(signal.get("impacted_order_ids", [])),
            "scenarios_count": len(scenarios),
            "recommended_actions": final_summary_from_state.get("recommended_actions", scenarios[:3]),
            "approval_queue_count": sum(
                1
                for s in scenarios
                if s.get("score_json", {}).get("needs_approval", False)
            ),
            "kpis": final_summary_from_state.get("kpis", _calculate_kpis(scenarios)),
            # LLM routing metadata
            "needs_review": needs_review,
            "early_exit_reason": early_exit_reason,
            "routing_steps": step_count,
            "routing_trace": routing_trace[-10:] if routing_trace else [],  # Keep last 10
        }

        # Try to add AI explanation if Bedrock is available
        try:
            from app.agents.bedrock_explain import generate_explanation

            explanation = generate_explanation(final_summary)
            final_summary["explanation"] = explanation
        except Exception as e:
            # Non-fatal, just log
            print(f"Could not generate explanation: {e}")
            final_summary["explanation"] = "Explanation unavailable"

        # Update pipeline run as done (or needs_review)
        pipeline_run.status = "needs_review" if needs_review else "done"
        pipeline_run.current_step = "completed"
        pipeline_run.progress = 1.0
        pipeline_run.completed_at = datetime.now(timezone.utc)
        pipeline_run.final_summary_json = json.dumps(final_summary)
        db.commit()

    except Exception as e:
        # Pipeline failed - update status and log error
        error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        try:
            pipeline_run = (
                db.query(PipelineRun)
                .filter(PipelineRun.pipeline_run_id == pipeline_run_id)
                .first()
            )

            if pipeline_run:
                pipeline_run.status = "failed"
                pipeline_run.current_step = "error"
                pipeline_run.completed_at = datetime.now(timezone.utc)
                pipeline_run.error_message = error_message
                db.commit()

                # Write decision log for failure
                log_id = str(uuid.uuid4())
                decision_log = DecisionLog(
                    log_id=log_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    pipeline_run_id=pipeline_run_id,
                    agent_name="SupervisorFailure",
                    input_summary=f"Pipeline run {pipeline_run_id} for disruption {disruption_id}",
                    output_summary=f"Pipeline failed: {str(e)}",
                    confidence_score=0.0,
                    rationale="Pipeline execution error",
                    human_decision="pending",
                )
                db.add(decision_log)
                db.commit()

        except Exception as commit_error:
            # Even error handling failed - log to console
            print(f"Failed to update pipeline status: {commit_error}")
            print(f"Original error: {error_message}")


def _calculate_kpis(recommendations: list[dict[str, Any]]) -> dict[str, float]:
    """
    Calculate KPIs from recommendations.

    Args:
        recommendations: List of recommendation dicts

    Returns:
        KPIs dict with cost, SLA risk, and labor metrics
    """
    if not recommendations:
        return {
            "estimated_cost": 0.0,
            "estimated_sla_risk_avg": 0.0,
            "estimated_labor_minutes": 0.0,
        }

    total_cost = 0.0
    total_sla_risk = 0.0
    total_labor = 0.0

    for rec in recommendations:
        score = rec.get("score_json", {})
        total_cost += score.get("cost_impact_usd", 0.0)
        total_sla_risk += score.get("sla_risk", 0.0)
        total_labor += score.get("labor_impact_minutes", 0.0)

    count = len(recommendations)
    return {
        "estimated_cost": round(total_cost, 2),
        "estimated_sla_risk_avg": round(total_sla_risk / count, 3) if count > 0 else 0.0,
        "estimated_labor_minutes": round(total_labor, 0),
    }
