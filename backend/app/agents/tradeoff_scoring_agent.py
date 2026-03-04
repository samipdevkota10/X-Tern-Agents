"""
Tradeoff Scoring Agent - Scores scenarios and determines approval needs.
Uses LLM reasoning when available, falls back to deterministic scoring.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.llm_agent import get_tradeoff_agent
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
        used_llm = False
        
        # Try LLM-based scoring first
        llm_agent = get_tradeoff_agent()
        if llm_agent.use_llm and scenarios:
            try:
                severity = signal.get("severity", 3)
                llm_scored = llm_agent.score_scenarios(scenarios, severity)
                if llm_scored:
                    scored_scenarios = llm_scored
                    used_llm = True
                    # Prepare DB updates from LLM results
                    for scenario in scored_scenarios:
                        if "scenario_id" in scenario and "score_json" in scenario:
                            scenario_score_updates.append({
                                "scenario_id": scenario["scenario_id"],
                                "score_json": scenario["score_json"],
                            })
            except Exception as e:
                print(f"LLM scoring failed, falling back to deterministic: {e}")
        
        # Fallback to deterministic scoring if LLM didn't work
        if not scored_scenarios:
            for scenario in scenarios:
                order_id = scenario["order_id"]
                order = order_map.get(order_id, {})
                
                # Extract required parameters for scoring
                action_type = scenario.get("action_type", "delay")
                order_priority = order.get("priority", "standard")
                plan_json = scenario.get("plan_json", {})
                order_line_count = len(order.get("lines", [])) or 1
                
                # Calculate scores using deterministic algorithm
                score = score_scenario(
                    action_type=action_type,
                    order_priority=order_priority,
                    plan=plan_json,
                    order_line_count=order_line_count,
                )
                
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
            1 for s in scored_scenarios if s.get("score_json", {}).get("needs_approval", False)
        )
        
        # Log decision with reasoning mode
        reasoning_mode = "LLM-powered analysis (AWS Bedrock)" if used_llm else "deterministic scoring algorithm"
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="TradeoffScoringAgent",
            input_summary=f"{len(scenarios)} scenarios to score",
            output_summary=f"Scored {len(scored_scenarios)} scenarios using {reasoning_mode}, {approval_count} need approval, updated {updated_count} in DB",
            confidence_score=0.95 if used_llm else 0.92,
            rationale=f"Used {reasoning_mode} to evaluate cost/SLA/complexity tradeoffs and flag {approval_count} high-risk scenarios for human review",
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
