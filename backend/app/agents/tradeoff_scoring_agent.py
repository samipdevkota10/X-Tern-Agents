"""
Tradeoff Scoring Agent - Scores scenarios and determines approval needs.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.scoring import score_scenario
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import update_scenario_scores, write_decision_log


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


def tradeoff_scoring_node(state: PipelineState) -> dict[str, Any]:
    """
    Tradeoff Scoring Agent node.
    
    Scores all scenarios and determines which need approval.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with scored scenarios
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal", {})
    scenarios = state.get("scenarios", [])
    
    write_status_safe(pipeline_run_id, "tradeoff_scoring", "started")
    
    try:
        impacted_orders = signal.get("impacted_orders", [])
        
        # Build order lookup
        order_map = {order["order_id"]: order for order in impacted_orders}
        
        # Score each scenario
        scored_scenarios = []
        scenario_score_updates = []
        
        for scenario in scenarios:
            order_id = scenario["order_id"]
            order = order_map.get(order_id, {})
            
            # Calculate scores
            score = score_scenario(scenario, order)
            
            # Add score to scenario
            scenario_with_score = {**scenario, "score_json": score}
            scored_scenarios.append(scenario_with_score)
            
            # Prepare DB update
            scenario_score_updates.append({
                "scenario_id": scenario["scenario_id"],
                "score_json": score,
            })
        
        # Update scores in database
        if scenario_score_updates:
            result = update_scenario_scores.invoke({"scenario_scores": scenario_score_updates})
            updated_count = result.get("updated", 0)
        else:
            updated_count = 0
        
        # Count approval needs
        approval_count = sum(
            1 for s in scored_scenarios if s["score_json"].get("needs_approval", False)
        )
        
        # Log decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="TradeoffScoringAgent",
            input_summary=f"{len(scenarios)} scenarios to score",
            output_summary=f"Scored {len(scored_scenarios)} scenarios, {approval_count} need approval, updated {updated_count} in DB",
            confidence_score=0.92,
            rationale="Applied deterministic scoring algorithm with SLA/cost/labor weights",
        )
        
        write_status_safe(
            pipeline_run_id,
            "tradeoff_scoring",
            "completed",
            {
                "scenarios_scored": len(scored_scenarios),
                "approval_needed": approval_count,
                "db_updated": updated_count,
            },
        )
        
        return {
            "scores": scored_scenarios,
            "step": "tradeoff_scoring",
        }
        
    except Exception as e:
        write_status_safe(pipeline_run_id, "tradeoff_scoring", "failed", {"error": str(e)})
        return {
            "error": f"Tradeoff scoring failed: {str(e)}",
            "step": "error",
        }
