"""
Execution engine for applying approved scenarios to operational database state.
This implements REAL human-in-the-loop gating - scenarios are only plans until approved.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import DecisionLog, Inventory, Order, OrderLine, Scenario, Substitution


def apply_scenario(
    db: Session, scenario_id: str, approver_id: str, approver_note: str
) -> dict[str, Any]:
    """
    Apply an approved scenario to the operational database state.
    This is the REAL execution gating - changes only happen on approval.

    Args:
        db: Database session
        scenario_id: Scenario ID to apply
        approver_id: User ID of approver
        approver_note: Approval note

    Returns:
        Summary dict of applied changes

    Raises:
        ValueError: If scenario not found, not pending, or constraints violated
    """
    # Load scenario with relationships
    scenario = (
        db.query(Scenario)
        .filter(Scenario.scenario_id == scenario_id)
        .first()
    )

    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    if scenario.status != "pending":
        raise ValueError(
            f"Scenario {scenario_id} is {scenario.status}, cannot apply"
        )

    # Decode plan and score
    try:
        plan = json.loads(scenario.plan_json)
        score = json.loads(scenario.score_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in scenario: {e}")

    # Apply changes based on action type
    action_type = scenario.action_type
    changes_summary: dict[str, Any] = {
        "scenario_id": scenario_id,
        "action_type": action_type,
        "order_id": scenario.order_id,
        "changes": [],
    }

    if action_type == "delay":
        changes_summary["changes"] = _apply_delay(db, scenario, plan)
    elif action_type == "reroute":
        changes_summary["changes"] = _apply_reroute(db, scenario, plan)
    elif action_type == "substitute":
        changes_summary["changes"] = _apply_substitute(db, scenario, plan)
    elif action_type == "resequence":
        changes_summary["changes"] = _apply_resequence(db, scenario, plan)
    elif action_type == "expedite":
        changes_summary["changes"] = _apply_expedite(db, scenario, plan)
    elif action_type == "split":
        changes_summary["changes"] = _apply_split(db, scenario, plan)
    else:
        raise ValueError(f"Unknown action type: {action_type}")

    # Mark scenario as approved
    scenario.status = "approved"

    # Discard all other pending scenarios for this order (superseded by approval)
    other_pending = (
        db.query(Scenario)
        .filter(
            Scenario.disruption_id == scenario.disruption_id,
            Scenario.order_id == scenario.order_id,
            Scenario.scenario_id != scenario_id,
            Scenario.status == "pending",
        )
        .all()
    )
    for other in other_pending:
        other.status = "rejected"

    # Create decision log entry
    log_id = str(uuid.uuid4())
    decision_log = DecisionLog(
        log_id=log_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        pipeline_run_id=plan.get("pipeline_run_id", "manual"),
        agent_name="HumanApproval",
        input_summary=f"Approve scenario {scenario_id} ({action_type}) for order {scenario.order_id}",
        output_summary=json.dumps(changes_summary),
        confidence_score=1.0,
        rationale=f"Human approval by {approver_id}",
        human_decision="approved",
        approver_id=approver_id,
        approver_note=approver_note,
        override_value=None,
    )
    db.add(decision_log)

    # Commit all changes
    db.commit()

    changes_summary["decision_log_id"] = log_id
    return changes_summary


def _apply_delay(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply delay action: update order status and promised ship time.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict

    Returns:
        List of changes made
    """
    order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
    if not order:
        raise ValueError(f"Order {scenario.order_id} not found")

    changes = []

    # Update status to delayed
    old_status = order.status
    order.status = "delayed"
    changes.append(
        {
            "field": "status",
            "old_value": old_status,
            "new_value": "delayed",
        }
    )

    # Update promised ship time
    delay_hours = plan.get("delay_hours", 24)
    old_ship_time = order.promised_ship_time
    new_ship_time = old_ship_time + timedelta(hours=delay_hours)
    order.promised_ship_time = new_ship_time
    changes.append(
        {
            "field": "promised_ship_time",
            "old_value": old_ship_time.isoformat(),
            "new_value": new_ship_time.isoformat(),
            "delay_hours": delay_hours,
        }
    )

    return changes


def _apply_reroute(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply reroute action: change order DC and adjust inventory reservations.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict

    Returns:
        List of changes made

    Raises:
        ValueError: If insufficient inventory at target DC
    """
    order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
    if not order:
        raise ValueError(f"Order {scenario.order_id} not found")

    old_dc = order.dc
    new_dc = plan.get("target_dc")
    if not new_dc:
        # Derive target DC when plan omits it (e.g. LLM or older rules-generated scenarios)
        new_dc = "DC2" if old_dc == "DC1" else "DC1"

    changes = []

    # Check inventory availability at new DC for all order lines
    order_lines = db.query(OrderLine).filter(OrderLine.order_id == scenario.order_id).all()

    for line in order_lines:
        inv = (
            db.query(Inventory)
            .filter(Inventory.dc == new_dc, Inventory.sku == line.sku)
            .first()
        )

        if not inv:
            raise ValueError(
                f"No inventory record for SKU {line.sku} at {new_dc}"
            )

        available = inv.on_hand - inv.reserved
        if available < line.qty:
            raise ValueError(
                f"Insufficient inventory for SKU {line.sku} at {new_dc}: "
                f"need {line.qty}, available {available}"
            )

    # Apply inventory changes
    for line in order_lines:
        # Reserve at new DC
        new_inv = (
            db.query(Inventory)
            .filter(Inventory.dc == new_dc, Inventory.sku == line.sku)
            .first()
        )
        old_reserved_new = new_inv.reserved
        new_inv.reserved += line.qty
        changes.append(
            {
                "type": "inventory_reserve",
                "dc": new_dc,
                "sku": line.sku,
                "qty": line.qty,
                "old_reserved": old_reserved_new,
                "new_reserved": new_inv.reserved,
            }
        )

        # Release at old DC (if previously reserved)
        old_inv = (
            db.query(Inventory)
            .filter(Inventory.dc == old_dc, Inventory.sku == line.sku)
            .first()
        )
        if old_inv and old_inv.reserved >= line.qty:
            old_reserved_old = old_inv.reserved
            old_inv.reserved -= line.qty
            changes.append(
                {
                    "type": "inventory_release",
                    "dc": old_dc,
                    "sku": line.sku,
                    "qty": line.qty,
                    "old_reserved": old_reserved_old,
                    "new_reserved": old_inv.reserved,
                }
            )

    # Update order DC
    order.dc = new_dc
    changes.append(
        {
            "type": "order_dc_change",
            "field": "dc",
            "old_value": old_dc,
            "new_value": new_dc,
        }
    )

    return changes


def _apply_substitute(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply substitute action: replace SKU in order lines.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict

    Returns:
        List of changes made
    """
    changes = []

    substitutions = plan.get("substitutions", [])
    if not substitutions:
        # Fallback: derive from order lines + substitutions table (e.g. legacy or LLM-generated plans)
        order_lines = (
            db.query(OrderLine)
            .filter(OrderLine.order_id == scenario.order_id)
            .all()
        )
        skus = [line.sku for line in order_lines]
        sub_rows = (
            db.query(Substitution)
            .filter(Substitution.sku.in_(skus))
            .all()
        )
        substitutions = [
            {
                "original_sku": row.sku,
                "substitute_sku": row.substitute_sku,
                "penalty_cost": row.penalty_cost,
            }
            for row in sub_rows
        ]
    if not substitutions:
        raise ValueError("Substitute plan missing substitutions list")

    for sub in substitutions:
        original_sku = sub.get("original_sku")
        substitute_sku = sub.get("substitute_sku")

        if not original_sku or not substitute_sku:
            raise ValueError("Substitution missing original_sku or substitute_sku")

        # Find and update order lines
        lines = (
            db.query(OrderLine)
            .filter(
                OrderLine.order_id == scenario.order_id,
                OrderLine.sku == original_sku,
            )
            .all()
        )

        for line in lines:
            old_sku = line.sku
            line.sku = substitute_sku
            changes.append(
                {
                    "type": "sku_substitution",
                    "line_id": line.line_id,
                    "old_sku": old_sku,
                    "new_sku": substitute_sku,
                    "qty": line.qty,
                    "penalty_cost": sub.get("penalty_cost", 0.0),
                }
            )

    return changes


def _apply_expedite(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply expedite action: prioritize order for faster fulfillment.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict

    Returns:
        List of changes made
    """
    order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
    if not order:
        raise ValueError(f"Order {scenario.order_id} not found")

    changes = []

    # Prioritize in work queue and mark as planned for expedited handling
    old_priority = order.sequence_priority
    order.sequence_priority = 1  # 1 = highest priority
    changes.append(
        {
            "field": "sequence_priority",
            "old_value": old_priority,
            "new_value": 1,
            "description": "Expedited - prioritized for fast fulfillment",
        }
    )

    old_status = order.status
    order.status = "planned"
    changes.append(
        {
            "field": "status",
            "old_value": old_status,
            "new_value": "planned",
        }
    )

    return changes


def _apply_split(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply split action: approve partial ship now + backorder for out-of-stock items.

    Records the split plan (ship available now, backorder rest) for warehouse execution.
    Does not modify inventory/order lines directly - warehouse staff executes per plan.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict with summary, what_happened, what_to_do

    Returns:
        List of changes made
    """
    order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
    if not order:
        raise ValueError(f"Order {scenario.order_id} not found")

    changes = []

    # Mark order as planned for split fulfillment - warehouse will execute per plan
    old_status = order.status
    order.status = "planned"
    changes.append(
        {
            "field": "status",
            "old_value": old_status,
            "new_value": "planned",
            "description": "Split shipment approved - partial ship now, backorder rest",
        }
    )

    # Record the split plan for warehouse execution (no inventory/line changes here)
    split_plan = {
        "summary": plan.get("summary", "Split: ship available now, backorder out-of-stock"),
        "what_happened": plan.get("what_happened"),
        "what_to_do": plan.get("what_to_do"),
    }
    changes.append(
        {
            "type": "split_plan_approved",
            "order_id": scenario.order_id,
            "plan": split_plan,
            "description": "Approved for warehouse: execute partial ship + backorder per plan",
        }
    )

    return changes


def _apply_resequence(
    db: Session, scenario: Scenario, plan: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Apply resequence action: update order priority in work queue.

    Args:
        db: Database session
        scenario: Scenario object
        plan: Plan JSON dict

    Returns:
        List of changes made
    """
    order = db.query(Order).filter(Order.order_id == scenario.order_id).first()
    if not order:
        raise ValueError(f"Order {scenario.order_id} not found")

    changes = []

    # Update status to planned
    old_status = order.status
    order.status = "planned"
    changes.append(
        {
            "field": "status",
            "old_value": old_status,
            "new_value": "planned",
        }
    )

    # Set sequence priority to urgent
    old_priority = order.sequence_priority
    order.sequence_priority = 1  # 1 = urgent
    changes.append(
        {
            "field": "sequence_priority",
            "old_value": old_priority,
            "new_value": 1,
            "description": "Prioritized in work queue",
        }
    )

    return changes
