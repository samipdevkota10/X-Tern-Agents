"""
Deterministic business rules for scenario generation.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid


def generate_delay_scenario(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a delay scenario for an order.
    
    Args:
        order: Order dictionary
        disruption: Disruption details
        constraints: Constraint data
        
    Returns:
        Scenario dictionary
    """
    # Parse promised ship time
    promised_time = datetime.fromisoformat(order["promised_ship_time"].replace("Z", "+00:00"))
    cutoff_time = datetime.fromisoformat(order["cutoff_time"].replace("Z", "+00:00"))
    
    # Determine delay duration based on disruption
    if disruption["type"] == "late_truck":
        delay_minutes = disruption["details"].get("delay_minutes", 120)
    elif disruption["type"] == "machine_down":
        delay_minutes = disruption["details"].get("expected_recovery_minutes", 90)
    else:
        delay_minutes = 120  # Default 2 hours
    
    new_ship_time = promised_time + timedelta(minutes=delay_minutes)
    cutoff_exceeded = new_ship_time > cutoff_time
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "delay",
        "plan_json": {
            "action": "delay_order",
            "original_ship_time": order["promised_ship_time"],
            "new_ship_time": new_ship_time.isoformat(),
            "delay_minutes": delay_minutes,
            "cutoff_exceeded": cutoff_exceeded,
            "reason": f"Delayed due to {disruption['type']}",
            "assumptions": [
                f"Disruption will be resolved in {delay_minutes} minutes",
                "No additional delays expected",
            ],
        },
        "status": "pending",
    }


def generate_reroute_scenario(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Generate a reroute scenario for an order.
    
    Args:
        order: Order dictionary
        disruption: Disruption details
        constraints: Constraint data with inventory info
        
    Returns:
        Scenario dictionary or None if not feasible
    """
    current_dc = order["dc"]
    target_dc = "DC2" if current_dc == "DC1" else "DC1"
    
    # Check if target DC has inventory
    order_inventory = constraints.get("per_order_inventory", {}).get(order["order_id"], {})
    target_inventory = order_inventory.get(target_dc, {})
    
    # Check availability for all SKUs
    sufficient = True
    for line in order.get("lines", []):
        sku = line["sku"]
        qty = line["qty"]
        available = target_inventory.get(sku, {}).get("available", 0)
        if available < qty:
            sufficient = False
            break
    
    if not sufficient:
        return None  # Cannot reroute if inventory insufficient
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "reroute",
        "plan_json": {
            "action": "reroute_to_dc",
            "original_dc": current_dc,
            "target_dc": target_dc,
            "availability_sufficient": sufficient,
            "reason": f"Reroute from {current_dc} to {target_dc} due to {disruption['type']}",
            "assumptions": [
                f"Inventory available at {target_dc}",
                "Transfer can complete before cutoff",
            ],
        },
        "status": "pending",
    }


def generate_substitute_scenario(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Generate substitute scenarios for an order.
    
    Args:
        order: Order dictionary
        disruption: Disruption details
        constraints: Constraint data with substitution rules
        
    Returns:
        List of scenario dictionaries (one per substitutable SKU)
    """
    scenarios = []
    substitution_rules = constraints.get("substitution_rules", [])
    
    # Build SKU to substitution map
    sub_map = {rule["sku"]: rule for rule in substitution_rules}
    
    for line in order.get("lines", []):
        sku = line["sku"]
        if sku in sub_map:
            sub_rule = sub_map[sku]
            scenarios.append({
                "scenario_id": str(uuid.uuid4()),
                "disruption_id": disruption["id"],
                "order_id": order["order_id"],
                "action_type": "substitute",
                "plan_json": {
                    "action": "substitute_sku",
                    "original_sku": sku,
                    "substitute_sku": sub_rule["substitute_sku"],
                    "penalty_cost": sub_rule["penalty_cost"],
                    "quantity": line["qty"],
                    "reason": f"Substitute {sku} with {sub_rule['substitute_sku']} due to {disruption['type']}",
                    "assumptions": [
                        "Substitute SKU is acceptable to customer",
                        "Substitute inventory is available",
                    ],
                },
                "status": "pending",
            })
    
    return scenarios


def generate_resequence_scenario(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a resequence scenario for an order.
    
    Args:
        order: Order dictionary
        disruption: Disruption details
        constraints: Constraint data with capacity info
        
    Returns:
        Scenario dictionary
    """
    # Check capacity constraints
    capacities = constraints.get("capacities", [])
    capacity_sufficient = any(
        cap.get("dc") == order["dc"] and not cap.get("downtime_flag", False)
        for cap in capacities
    )
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "resequence",
        "plan_json": {
            "action": "prioritize_order",
            "priority_level": "high",
            "original_priority": order.get("priority", "standard"),
            "availability_sufficient": capacity_sufficient,
            "reason": f"Prioritize order in queue due to {disruption['type']}",
            "assumptions": [
                "Capacity available for priority handling",
                "Other orders can be delayed slightly",
            ],
        },
        "status": "pending",
    }


def generate_scenarios_for_order(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Generate all feasible scenarios for a single order.
    
    Args:
        order: Order dictionary
        disruption: Disruption details
        constraints: Constraint data
        
    Returns:
        List of 2-6 scenario dictionaries
    """
    scenarios = []
    
    # Always generate delay scenario
    scenarios.append(generate_delay_scenario(order, disruption, constraints))
    
    # Try reroute
    reroute = generate_reroute_scenario(order, disruption, constraints)
    if reroute:
        scenarios.append(reroute)
    
    # Try substitutes
    substitutes = generate_substitute_scenario(order, disruption, constraints)
    scenarios.extend(substitutes[:2])  # Limit to 2 substitute scenarios
    
    # Always generate resequence
    scenarios.append(generate_resequence_scenario(order, disruption, constraints))
    
    return scenarios[:6]  # Cap at 6 scenarios per order
