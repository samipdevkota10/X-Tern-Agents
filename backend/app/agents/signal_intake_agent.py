"""
Signal Intake Agent - Identifies disruption and impacted orders.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import read_disruption, read_open_orders, write_decision_log


def log_agent_step(
    pipeline_run_id: str,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    confidence_score: float,
    rationale: str,
) -> None:
    """
    Helper to log agent decision step.
    
    Args:
        pipeline_run_id: Pipeline run ID
        agent_name: Name of the agent
        input_summary: Summary of inputs
        output_summary: Summary of outputs
        confidence_score: Confidence score (0..1)
        rationale: Reasoning explanation
    """
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


def signal_intake_node(state: PipelineState) -> dict[str, Any]:
    """
    Signal Intake Agent node.
    
    Reads disruption details and identifies impacted orders.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with signal data
    """
    pipeline_run_id = state["pipeline_run_id"]
    disruption_id = state["disruption_id"]
    
    write_status_safe(pipeline_run_id, "signal_intake", "started")
    
    try:
        # Read disruption
        disruption = read_disruption.invoke({"disruption_id": disruption_id})
        
        if "error" in disruption:
            return {
                "error": f"Disruption not found: {disruption_id}",
                "step": "error",
            }
        
        # Read all open orders
        all_orders = read_open_orders.invoke({})
        
        # Identify impacted orders based on disruption type
        impacted_orders = _identify_impacted_orders(disruption, all_orders)
        
        # Build normalized signal
        signal = {
            "disruption_id": disruption["id"],
            "type": disruption["type"],
            "severity": disruption["severity"],
            "occurred_at": disruption["timestamp"],
            "details": disruption["details"],
            "impacted_order_ids": [o["order_id"] for o in impacted_orders],
            "impacted_orders": impacted_orders,
            "impacted_reason": _get_impact_reason(disruption),
        }
        
        # Log decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="SignalIntakeAgent",
            input_summary=f"Disruption {disruption_id} type={disruption['type']}",
            output_summary=f"Identified {len(impacted_orders)} impacted orders",
            confidence_score=0.90,
            rationale=f"Applied {disruption['type']} impact rules to {len(all_orders)} open orders",
        )
        
        write_status_safe(
            pipeline_run_id,
            "signal_intake",
            "completed",
            {"impacted_orders": len(impacted_orders)},
        )
        
        return {
            "signal": signal,
            "step": "signal_intake",
        }
        
    except Exception as e:
        write_status_safe(pipeline_run_id, "signal_intake", "failed", {"error": str(e)})
        return {
            "error": f"Signal intake failed: {str(e)}",
            "step": "error",
        }


def _identify_impacted_orders(
    disruption: dict[str, Any], all_orders: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Identify which orders are impacted by the disruption.
    
    Args:
        disruption: Disruption details
        all_orders: List of all open orders
        
    Returns:
        List of impacted orders
    """
    impacted = []
    details = disruption.get("details", {})
    disruption_type = disruption["type"]
    
    if disruption_type == "late_truck":
        # Orders depending on inbound SKUs from this truck
        # For demo: select high-priority orders and some standard ones
        for order in all_orders:
            if order.get("priority") in ["expedited", "vip"]:
                impacted.append(order)
            elif order.get("priority") == "standard" and len(impacted) < 8:
                impacted.append(order)
            if len(impacted) >= 10:
                break
    
    elif disruption_type == "stockout":
        # Orders containing the out-of-stock SKU at the affected DC
        sku = details.get("sku")
        dc = details.get("dc")
        for order in all_orders:
            if order.get("dc") == dc:
                for line in order.get("lines", []):
                    if line.get("sku") == sku:
                        impacted.append(order)
                        break
            # Also add some orders from same DC even if SKU doesn't match
            elif order.get("dc") == dc and len(impacted) < 8:
                impacted.append(order)
            if len(impacted) >= 10:
                break
    
    elif disruption_type == "machine_down":
        # Orders at the affected DC with soon cutoffs
        dc = details.get("dc")
        for order in all_orders:
            if order.get("dc") == dc:
                impacted.append(order)
            elif len(impacted) < 8:  # Add some from other DC too
                impacted.append(order)
            if len(impacted) >= 10:
                break
    
    # Fallback: if no specific matching, take first N orders
    if not impacted and all_orders:
        impacted = all_orders[:10]
    
    return impacted[:10]  # Cap at 10 impacted orders


def _get_impact_reason(disruption: dict[str, Any]) -> str:
    """
    Generate human-readable impact reason.
    
    Args:
        disruption: Disruption details
        
    Returns:
        Impact reason string
    """
    disruption_type = disruption["type"]
    details = disruption.get("details", {})
    
    if disruption_type == "late_truck":
        truck_id = details.get("truck_id", "unknown")
        delay = details.get("delay_minutes", 0)
        return f"Truck {truck_id} delayed by {delay} minutes"
    elif disruption_type == "stockout":
        sku = details.get("sku", "unknown")
        dc = details.get("dc", "unknown")
        shortage = details.get("shortage_qty", 0)
        return f"SKU {sku} shortage of {shortage} units at {dc}"
    elif disruption_type == "machine_down":
        process = details.get("process", "unknown")
        dc = details.get("dc", "unknown")
        recovery = details.get("expected_recovery_minutes", 0)
        return f"{process} process down at {dc}, expected recovery in {recovery} minutes"
    
    return "Unknown disruption impact"
