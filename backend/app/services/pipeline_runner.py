"""
Pipeline runner service for executing LangGraph multi-agent pipeline.
Includes TRiSM (Trust, Risk, Security Management) governance evaluation.
Writes pipeline status to DynamoDB and results to S3 when USE_AWS=1.
"""
import json
import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DecisionLog, PipelineRun
from app.governance.trism import AIGovernanceFramework

# Governance framework instance
_governance = AIGovernanceFramework()


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

        # TRiSM Governance Evaluation
        trism_evaluation = None
        try:
            # Fetch decision logs for this pipeline run
            decision_logs = (
                db.query(DecisionLog)
                .filter(DecisionLog.pipeline_run_id == pipeline_run_id)
                .all()
            )
            decision_log_dicts = [
                {
                    "agent_name": log.agent_name,
                    "rationale": log.rationale,
                    "confidence_score": log.confidence_score,
                    "human_decision": log.human_decision,
                    "input_summary": log.input_summary,
                    "output_summary": log.output_summary,
                }
                for log in decision_logs
            ]

            # Run TRiSM evaluation
            trism_result = _governance.evaluate_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                scenarios=scenarios,
                decision_logs=decision_log_dicts,
            )
            trism_evaluation = trism_result.to_dict()

            # Escalate if TRiSM flagged critical issues
            if trism_result.approval_required and not needs_review:
                needs_review = True
                if not early_exit_reason:
                    early_exit_reason = f"TRiSM: {trism_result.risk_level.value} risk"

        except Exception as e:
            print(f"TRiSM evaluation failed (non-fatal): {e}")
            trism_evaluation = {"error": str(e), "evaluated_at": datetime.now(UTC).isoformat()}

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
            # TRiSM Governance
            "trism_evaluation": trism_evaluation,
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
        pipeline_run.completed_at = datetime.now(UTC)
        pipeline_run.final_summary_json = json.dumps(final_summary)
        db.commit()

        # When USE_AWS=1: write final status to DynamoDB and results to S3
        _write_aws_artifacts(
            pipeline_run_id,
            disruption_id,
            final_summary,
            scenarios=scenarios,
            status="completed",
        )

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
                pipeline_run.completed_at = datetime.now(UTC)
                pipeline_run.error_message = error_message
                db.commit()

                # Write decision log for failure
                log_id = str(uuid.uuid4())
                decision_log = DecisionLog(
                    log_id=log_id,
                    timestamp=datetime.now(UTC).isoformat(),
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

                # When USE_AWS=1: write failure status to DynamoDB (no S3 for failed runs)
                _write_aws_artifacts(
                    pipeline_run_id,
                    disruption_id,
                    {"error": error_message},
                    scenarios=[],
                    status="failed",
                )

        except Exception as commit_error:
            # Even error handling failed - log to console
            print(f"Failed to update pipeline status: {commit_error}")
            print(f"Original error: {error_message}")


def _json_safe(obj: Any) -> Any:
    """Convert object to JSON-serializable form (handles datetime, etc.)."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return obj


def _write_aws_artifacts(
    pipeline_run_id: str,
    disruption_id: str,
    final_summary: dict[str, Any],
    *,
    scenarios: list[dict[str, Any]] | None = None,
    status: str,
) -> None:
    """
    Write pipeline artifacts to AWS (DynamoDB + S3) when USE_AWS=1.
    Non-fatal: logs errors but never raises.

    Args:
        pipeline_run_id: Pipeline run ID
        disruption_id: Disruption ID
        final_summary: Final summary dict to store
        scenarios: Full scenario list for S3 persistence (completed runs only)
        status: completed or failed
    """
    if not settings.USE_AWS:
        return

    # 1. DynamoDB: write final pipeline status
    try:
        from app.aws.dynamo_status import write_status_safe

        write_status_safe(
            pipeline_run_id,
            "pipeline_complete",
            status,
            {"disruption_id": disruption_id},
        )
    except Exception as e:
        print(f"DynamoDB pipeline status write failed (non-fatal): {e}")

    # 2. S3: store pipeline run result JSON (for completed and failed - audit trail)
    try:
        import boto3
        from botocore.exceptions import ClientError

        bucket = settings.S3_BUCKET_NAME
        if not bucket:
            return

        key = f"pipeline_runs/{pipeline_run_id}.json"
        scenarios_ser = _json_safe(scenarios) if scenarios else []
        payload = {
            "pipeline_run_id": pipeline_run_id,
            "disruption_id": disruption_id,
            "status": status,
            "ts_iso": datetime.now(UTC).isoformat(),
            "final_summary": _json_safe(final_summary),
            "scenarios": scenarios_ser,
        }
        body = json.dumps(payload, indent=2)

        kwargs = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        s3 = boto3.client("s3", **kwargs)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
    except ImportError:
        pass  # boto3 not installed
    except ClientError as e:
        print(f"S3 pipeline result write failed (non-fatal): {e}")
    except Exception as e:
        print(f"S3 write unexpected error (non-fatal): {e}")


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
