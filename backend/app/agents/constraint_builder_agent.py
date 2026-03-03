"""
Constraint Builder Agent - Gathers operational constraints.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.state import PipelineState
from app.aws.dynamo_status import write_status_safe
from app.mcp.tools import (
    read_capacity,
    read_inbound_status,
    read_inventory,
    read_substitutions,
    write_decision_log,
)


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


def constraint_builder_node(state: PipelineState) -> dict[str, Any]:
    """
    Constraint Builder Agent node.
    
    Gathers inventory, capacity, and substitution constraints.
    
    Args:
        state: Current pipeline state
        
    Returns:
        State updates with constraints data
    """
    pipeline_run_id = state["pipeline_run_id"]
    signal = state.get("signal", {})
    
    write_status_safe(pipeline_run_id, "constraint_builder", "started")
    
    try:
        impacted_orders = signal.get("impacted_orders", [])
        disruption = signal
        
        # Gather inventory for each impacted order
        per_order_inventory = {}
        all_skus = set()
        
        for order in impacted_orders:
            order_id = order["order_id"]
            dc = order["dc"]
            per_order_inventory[order_id] = {}
            
            for line in order.get("lines", []):
                sku = line["sku"]
                all_skus.add(sku)
                
                # Check inventory at current DC
                inv_current = read_inventory.invoke({"dc": dc, "sku": sku})
                
                # Check inventory at alternate DC
                alt_dc = "DC2" if dc == "DC1" else "DC1"
                inv_alt = read_inventory.invoke({"dc": alt_dc, "sku": sku})
                
                per_order_inventory[order_id][dc] = {
                    sku: {
                        "on_hand": inv_current.get("on_hand", 0),
                        "reserved": inv_current.get("reserved", 0),
                        "available": inv_current.get("available", 0),
                    }
                }
                per_order_inventory[order_id][alt_dc] = {
                    sku: {
                        "on_hand": inv_alt.get("on_hand", 0),
                        "reserved": inv_alt.get("reserved", 0),
                        "available": inv_alt.get("available", 0),
                    }
                }
        
        # Get inbound status if late_truck disruption
        inbound_eta = None
        if disruption.get("type") == "late_truck":
            truck_id = disruption.get("details", {}).get("truck_id")
            if truck_id:
                inbound_status = read_inbound_status.invoke({"truck_id": truck_id})
                if "error" not in inbound_status:
                    inbound_eta = inbound_status.get("eta")
        
        # Get capacity for affected processes
        capacities = []
        if disruption.get("type") == "machine_down":
            process = disruption.get("details", {}).get("process", "packing")
            capacities = read_capacity.invoke({"process": process})
        else:
            # Get packing capacity as default
            capacities = read_capacity.invoke({"process": "packing"})
        
        # Get substitution rules for all SKUs
        substitution_rules = []
        if all_skus:
            substitution_rules = read_substitutions.invoke({"skus": list(all_skus)})
        
        # Build cutoff map
        cutoffs = {}
        for order in impacted_orders:
            cutoffs[order["order_id"]] = {
                "cutoff_time": order.get("cutoff_time"),
                "promised_ship_time": order.get("promised_ship_time"),
            }
        
        constraints = {
            "cutoffs": cutoffs,
            "per_order_inventory": per_order_inventory,
            "inbound_eta": inbound_eta,
            "capacities": capacities,
            "substitution_rules": substitution_rules,
        }
        
        # Log decision
        log_agent_step(
            pipeline_run_id=pipeline_run_id,
            agent_name="ConstraintBuilderAgent",
            input_summary=f"{len(impacted_orders)} impacted orders, {len(all_skus)} unique SKUs",
            output_summary=f"Gathered inventory for {len(per_order_inventory)} orders, {len(substitution_rules)} substitution rules",
            confidence_score=0.85,
            rationale="Retrieved inventory, capacity, and substitution data from operational systems",
        )
        
        write_status_safe(
            pipeline_run_id,
            "constraint_builder",
            "completed",
            {"orders": len(impacted_orders), "skus": len(all_skus)},
        )
        
        return {
            "constraints": constraints,
            "step": "constraint_builder",
        }
        
    except Exception as e:
        write_status_safe(
            pipeline_run_id, "constraint_builder", "failed", {"error": str(e)}
        )
        return {
            "error": f"Constraint builder failed: {str(e)}",
            "step": "error",
        }
