"""
Deterministic business rules for scenario generation.
"""
from datetime import datetime, timedelta
from typing import Any
import uuid


def _format_disruption_type(dtype: str) -> str:
    """Convert disruption type to human-readable format."""
    return dtype.replace("_", " ").title()


def generate_delay_scenario(
    order: dict[str, Any],
    disruption: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a delay scenario for an order.
    """
    promised_time = datetime.fromisoformat(order["promised_ship_time"].replace("Z", "+00:00"))
    cutoff_time = datetime.fromisoformat(order["cutoff_time"].replace("Z", "+00:00"))
    
    if disruption["type"] == "late_truck":
        delay_minutes = disruption["details"].get("delay_minutes", 120)
    elif disruption["type"] == "machine_down":
        delay_minutes = disruption["details"].get("expected_recovery_minutes", 90)
    else:
        delay_minutes = 120
    
    new_ship_time = promised_time + timedelta(minutes=delay_minutes)
    cutoff_exceeded = new_ship_time > cutoff_time
    delay_hours = delay_minutes // 60
    delay_remaining = delay_minutes % 60
    
    dtype = _format_disruption_type(disruption["type"])
    description = disruption["details"].get("description", f"{dtype} event")
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "delay",
        "plan_json": {
            "summary": f"Accept delay of {delay_hours}h {delay_remaining}m for order {order['order_id']}",
            "what_happened": f"{description}. This impacts order {order['order_id']} ({order.get('priority', 'standard')} priority) which was scheduled to ship by {promised_time.strftime('%I:%M %p')}.",
            "what_to_do": f"Accept the delay and reschedule shipment to {new_ship_time.strftime('%I:%M %p')}. {'⚠️ This will exceed the cutoff time - customer notification required.' if cutoff_exceeded else 'Shipment will still meet cutoff deadline.'}",
            "how_to_handle": f"1. Update order status to 'delayed' in system\n2. Set new ship time to {new_ship_time.strftime('%I:%M %p')}\n3. {'Notify customer about the delay via email/SMS' if cutoff_exceeded else 'No customer notification needed'}\n4. Monitor disruption resolution progress\n5. Re-queue order once disruption clears",
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
    """
    current_dc = order["dc"]
    target_dc = "DC2" if current_dc == "DC1" else "DC1"
    
    order_inventory = constraints.get("per_order_inventory", {}).get(order["order_id"], {})
    target_inventory = order_inventory.get(target_dc, {})
    
    sufficient = True
    for line in order.get("lines", []):
        sku = line["sku"]
        qty = line["qty"]
        available = target_inventory.get(sku, {}).get("available", 0)
        if available < qty:
            sufficient = False
            break
    
    if not sufficient:
        return None
    
    dtype = _format_disruption_type(disruption["type"])
    description = disruption["details"].get("description", f"{dtype} event")
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "reroute",
        "plan_json": {
            "summary": f"Reroute order {order['order_id']} from {current_dc} to {target_dc}",
            "what_happened": f"{description}. Order {order['order_id']} ({order.get('priority', 'standard')} priority) is affected at {current_dc} and needs an alternative fulfillment path.",
            "what_to_do": f"Transfer fulfillment to {target_dc} which has all required inventory available. This avoids the disruption entirely and maintains the original shipping timeline.",
            "how_to_handle": f"1. Transfer order {order['order_id']} to {target_dc} queue\n2. Verify inventory reservation at {target_dc}\n3. Release inventory hold at {current_dc}\n4. Prioritize picking at {target_dc} to meet original SLA\n5. Update shipping labels with new origin DC",
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
    """
    scenarios = []
    substitution_rules = constraints.get("substitution_rules", [])
    sub_map = {rule["sku"]: rule for rule in substitution_rules}
    
    dtype = _format_disruption_type(disruption["type"])
    description = disruption["details"].get("description", f"{dtype} event")
    
    for line in order.get("lines", []):
        sku = line["sku"]
        if sku in sub_map:
            sub_rule = sub_map[sku]
            penalty = sub_rule["penalty_cost"]
            scenarios.append({
                "scenario_id": str(uuid.uuid4()),
                "disruption_id": disruption["id"],
                "order_id": order["order_id"],
                "action_type": "substitute",
                "plan_json": {
                    "summary": f"Substitute {sku} with {sub_rule['substitute_sku']} (${penalty:.2f} penalty)",
                    "what_happened": f"{description}. Item {sku} in order {order['order_id']} is unavailable. A compatible substitute {sub_rule['substitute_sku']} is available.",
                    "what_to_do": f"Replace {line['qty']} units of {sku} with {sub_rule['substitute_sku']}. This incurs a ${penalty:.2f} substitution penalty but allows immediate fulfillment.",
                    "how_to_handle": f"1. Verify customer accepts substitution (check order preferences)\n2. Update order line from {sku} to {sub_rule['substitute_sku']}\n3. Reserve {line['qty']} units of substitute\n4. Log substitution for billing adjustment (${penalty:.2f})\n5. Include substitution notice in packing slip",
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
    """
    dtype = _format_disruption_type(disruption["type"])
    description = disruption["details"].get("description", f"{dtype} event")
    priority = order.get("priority", "standard")
    
    return {
        "scenario_id": str(uuid.uuid4()),
        "disruption_id": disruption["id"],
        "order_id": order["order_id"],
        "action_type": "resequence",
        "plan_json": {
            "summary": f"Prioritize order {order['order_id']} to front of queue",
            "what_happened": f"{description}. Order {order['order_id']} ({priority} priority) is at risk of missing its SLA due to the disruption backlog.",
            "what_to_do": f"Move order {order['order_id']} to high priority in the processing queue. This ensures it gets processed immediately once capacity is restored.",
            "how_to_handle": f"1. Flag order {order['order_id']} as 'urgent' in system\n2. Move to front of {order['dc']} processing queue\n3. Pre-stage inventory near packing area\n4. Assign dedicated picker when capacity resumes\n5. Have shipping labels pre-printed and ready",
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
    
    # Try substitutes (limit to 1)
    substitutes = generate_substitute_scenario(order, disruption, constraints)
    if substitutes:
        scenarios.append(substitutes[0])
    
    # Cap at 3 scenarios per order to reduce LLM costs
    return scenarios[:3]
