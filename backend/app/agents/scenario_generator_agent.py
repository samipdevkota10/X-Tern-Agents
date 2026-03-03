"""
Scenario Generator Agent - Creates response scenarios.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.rules import generate_scenarios_for_order
from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import write_decision_log, write_scenarios


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


def scenario_generator_node(state: PipelineState) -> dict[str, Any]:
    """
    Scenario Generator Agent node.
    
    Generates 2-6 scenarios per impacted order using deterministic rules.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with scenarios data
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal", {})
    constraints = state.get("constraints", {})
    
    write_status_safe(pipeline_run_id, "scenario_generator", "started")
    
    try:
        impacted_orders = signal.get("impacted_orders", [])
        disruption = {
            "id": signal["disruption_id"],
            "type": signal["type"],
            "severity": signal["severity"],
            "details": signal["details"],
        }
        
        all_scenarios = []
        
        # Generate scenarios for each impacted order
        for order in impacted_orders:
            scenarios = generate_scenarios_for_order(order, disruption, constraints)
            all_scenarios.extend(scenarios)
        
        # Persist scenarios to database
        if all_scenarios:
            result = write_scenarios.invoke({"scenarios": all_scenarios})
            created_count = result.get("created", 0)
        else:
            created_count = 0
        
        # Log decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="ScenarioGeneratorAgent",
            input_summary=f"{len(impacted_orders)} impacted orders",
            output_summary=f"Generated {len(all_scenarios)} scenarios, persisted {created_count} to DB",
            confidence_score=0.88,
            rationale=f"Applied deterministic scenario generation rules for {len(impacted_orders)} orders",
        )
        
        write_status_safe(
            pipeline_run_id,
            "scenario_generator",
            "completed",
            {"scenarios_generated": len(all_scenarios), "scenarios_persisted": created_count},
        )
        
        return {
            "scenarios": all_scenarios,
            "step": "scenario_generator",
        }
        
    except Exception as e:
        write_status_safe(
            pipeline_run_id, "scenario_generator", "failed", {"error": str(e)}
        )
        return {
            "error": f"Scenario generator failed: {str(e)}",
            "step": "error",
        }
