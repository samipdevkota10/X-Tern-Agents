"""
MCP Tools for disruption response planner.
Uses LangChain @tool decorator to expose SQLAlchemy DB operations.
All functions return pure Python dict/list types for LangChain compatibility.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models import (
    Capacity,
    DecisionLog,
    Disruption,
    InboundShipment,
    Inventory,
    Order,
    OrderLine,
    PipelineRun,
    Scenario,
    Substitution,
)
from app.db.session import SessionLocal


# Helper functions for JSON encoding/decoding
def json_dumps(obj: Any) -> str:
    """
    Safely encode Python object to JSON string.
    
    Args:
        obj: Python object to encode
        
    Returns:
        JSON string
    """
    try:
        return json.dumps(obj)
    except (TypeError, ValueError) as e:
        return json.dumps({"error": f"JSON encoding failed: {str(e)}"})


def json_loads(text: str) -> Any:
    """
    Safely decode JSON string to Python object.
    
    Args:
        text: JSON string to decode
        
    Returns:
        Decoded Python object or empty dict on error
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        return {"error": f"JSON decoding failed: {str(e)}"}


def ensure_iso8601(dt: datetime | str) -> str:
    """
    Ensure datetime is in ISO8601 string format.
    
    Args:
        dt: datetime object or string
        
    Returns:
        ISO8601 formatted string
    """
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


# MCP Tools
@tool
def read_open_orders() -> list[dict]:
    """
    Read all open orders with their line items.
    
    Returns:
        List of order dictionaries, each containing order details and lines.
    """
    db = SessionLocal()
    try:
        stmt = (
            select(Order)
            .where(Order.status == "open")
            .options(joinedload(Order.lines))
        )
        orders = db.execute(stmt).unique().scalars().all()
        
        result = []
        for order in orders:
            result.append({
                "order_id": order.order_id,
                "priority": order.priority,
                "promised_ship_time": ensure_iso8601(order.promised_ship_time),
                "cutoff_time": ensure_iso8601(order.cutoff_time),
                "dc": order.dc,
                "status": order.status,
                "lines": [
                    {"sku": line.sku, "qty": line.qty}
                    for line in order.lines
                ],
            })
        
        return result
    finally:
        db.close()


@tool
def read_inventory(dc: str, sku: str) -> dict:
    """
    Read inventory information for a specific DC and SKU.
    
    Args:
        dc: Distribution center identifier (e.g., 'DC1')
        sku: Stock keeping unit identifier
        
    Returns:
        Dictionary with on_hand, reserved, and available quantities.
    """
    db = SessionLocal()
    try:
        stmt = select(Inventory).where(
            Inventory.dc == dc,
            Inventory.sku == sku
        )
        inv = db.execute(stmt).scalar_one_or_none()
        
        if inv is None:
            return {
                "dc": dc,
                "sku": sku,
                "on_hand": 0,
                "reserved": 0,
                "available": 0,
                "error": "Inventory not found"
            }
        
        return {
            "dc": inv.dc,
            "sku": inv.sku,
            "on_hand": inv.on_hand,
            "reserved": inv.reserved,
            "available": inv.on_hand - inv.reserved,
        }
    finally:
        db.close()


@tool
def read_inbound_status(truck_id: str) -> dict:
    """
    Read inbound shipment status for a specific truck.
    
    Args:
        truck_id: Truck identifier (e.g., 'T123')
        
    Returns:
        Dictionary with truck details and SKU list.
    """
    db = SessionLocal()
    try:
        stmt = select(InboundShipment).where(InboundShipment.truck_id == truck_id)
        truck = db.execute(stmt).scalar_one_or_none()
        
        if truck is None:
            return {
                "truck_id": truck_id,
                "error": "Truck not found"
            }
        
        return {
            "truck_id": truck.truck_id,
            "eta": ensure_iso8601(truck.eta),
            "dc": truck.dc,
            "sku_list": json_loads(truck.sku_list_json),
        }
    finally:
        db.close()


@tool
def read_capacity(process: str) -> list[dict]:
    """
    Read capacity information for a specific process across all DCs.
    
    Args:
        process: Process name (e.g., 'picking', 'packing', 'shipping')
        
    Returns:
        List of capacity records for the given process.
    """
    db = SessionLocal()
    try:
        stmt = select(Capacity).where(Capacity.process == process)
        capacities = db.execute(stmt).scalars().all()
        
        return [
            {
                "cap_id": cap.cap_id,
                "dc": cap.dc,
                "process": cap.process,
                "capacity_per_hour": cap.capacity_per_hour,
                "downtime_flag": cap.downtime_flag,
            }
            for cap in capacities
        ]
    finally:
        db.close()


@tool
def write_scenarios(scenarios: list[dict]) -> dict:
    """
    Insert new scenario records into the database.
    
    Args:
        scenarios: List of scenario dictionaries with required keys:
            - disruption_id, order_id, action_type, plan_json
            - score_json (optional, can be added later)
            
    Returns:
        Dictionary with count of created scenarios.
    """
    db = SessionLocal()
    try:
        created_count = 0
        for scenario_data in scenarios:
            # Validate required keys
            required_keys = ["disruption_id", "order_id", "action_type", "plan_json"]
            if not all(k in scenario_data for k in required_keys):
                continue
            
            # Use provided scenario_id or generate new one
            scenario_id = scenario_data.get("scenario_id", str(uuid.uuid4()))
            
            # Default empty score if not provided
            score_json = scenario_data.get("score_json", {})
            
            scenario = Scenario(
                scenario_id=scenario_id,
                disruption_id=scenario_data["disruption_id"],
                order_id=scenario_data["order_id"],
                action_type=scenario_data["action_type"],
                plan_json=json_dumps(scenario_data["plan_json"]),
                score_json=json_dumps(score_json),
                status=scenario_data.get("status", "pending"),
                used_llm=scenario_data.get("used_llm", False),
                llm_rationale=scenario_data.get("llm_rationale"),
                created_at=datetime.now(timezone.utc),
            )
            db.add(scenario)
            created_count += 1
        
        db.commit()
        return {"created": created_count}
    except Exception as e:
        db.rollback()
        return {"created": 0, "error": str(e)}
    finally:
        db.close()


@tool
def get_pending_scenarios() -> list[dict]:
    """
    Read all pending scenarios with disruption and order context.
    
    Returns:
        List of pending scenario dictionaries with full context.
    """
    db = SessionLocal()
    try:
        stmt = (
            select(Scenario)
            .where(Scenario.status == "pending")
            .options(joinedload(Scenario.disruption), joinedload(Scenario.order))
        )
        scenarios = db.execute(stmt).unique().scalars().all()
        
        result = []
        for scenario in scenarios:
            result.append({
                "scenario_id": scenario.scenario_id,
                "action_type": scenario.action_type,
                "status": scenario.status,
                "created_at": ensure_iso8601(scenario.created_at),
                "disruption": {
                    "id": scenario.disruption.id,
                    "type": scenario.disruption.type,
                    "severity": scenario.disruption.severity,
                    "timestamp": ensure_iso8601(scenario.disruption.timestamp),
                    "details": json_loads(scenario.disruption.details_json),
                },
                "order": {
                    "order_id": scenario.order.order_id,
                    "priority": scenario.order.priority,
                    "dc": scenario.order.dc,
                    "promised_ship_time": ensure_iso8601(scenario.order.promised_ship_time),
                },
                "plan": json_loads(scenario.plan_json),
                "score": json_loads(scenario.score_json),
            })
        
        return result
    finally:
        db.close()


@tool
def approve_scenario(scenario_id: str, approver: str, note: str) -> dict:
    """
    Approve a scenario and log the decision.
    
    Args:
        scenario_id: Scenario identifier
        approver: Approver user identifier
        note: Approval note/comment
        
    Returns:
        Dictionary with approval status.
    """
    db = SessionLocal()
    try:
        # Update scenario status
        stmt = select(Scenario).where(Scenario.scenario_id == scenario_id)
        scenario = db.execute(stmt).scalar_one_or_none()
        
        if scenario is None:
            return {"success": False, "error": "Scenario not found"}
        
        scenario.status = "approved"
        
        # Create decision log entry
        log_entry = DecisionLog(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pipeline_run_id=str(uuid.uuid4()),  # Generate new run ID
            agent_name="HumanApproval",
            input_summary=f"Scenario {scenario_id} approval request",
            output_summary=f"Scenario {scenario_id} approved by {approver}",
            confidence_score=1.0,
            rationale=f"Human approval: {note}",
            human_decision="approved",
            approver_id=approver,
            approver_note=note,
            override_value=None,
        )
        db.add(log_entry)
        
        db.commit()
        return {
            "success": True,
            "scenario_id": scenario_id,
            "status": "approved",
            "log_id": log_entry.log_id,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@tool
def reject_scenario(scenario_id: str, approver: str, note: str) -> dict:
    """
    Reject a scenario and log the decision.
    
    Args:
        scenario_id: Scenario identifier
        approver: Approver user identifier
        note: Rejection note/comment
        
    Returns:
        Dictionary with rejection status.
    """
    db = SessionLocal()
    try:
        # Update scenario status
        stmt = select(Scenario).where(Scenario.scenario_id == scenario_id)
        scenario = db.execute(stmt).scalar_one_or_none()
        
        if scenario is None:
            return {"success": False, "error": "Scenario not found"}
        
        scenario.status = "rejected"
        
        # Create decision log entry
        log_entry = DecisionLog(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            pipeline_run_id=str(uuid.uuid4()),  # Generate new run ID
            agent_name="HumanApproval",
            input_summary=f"Scenario {scenario_id} approval request",
            output_summary=f"Scenario {scenario_id} rejected by {approver}",
            confidence_score=1.0,
            rationale=f"Human rejection: {note}",
            human_decision="rejected",
            approver_id=approver,
            approver_note=note,
            override_value=None,
        )
        db.add(log_entry)
        
        db.commit()
        return {
            "success": True,
            "scenario_id": scenario_id,
            "status": "rejected",
            "log_id": log_entry.log_id,
        }
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@tool
def read_disruption(disruption_id: str) -> dict:
    """
    Read a specific disruption by ID.
    
    Args:
        disruption_id: Disruption identifier
        
    Returns:
        Dictionary with disruption details.
    """
    db = SessionLocal()
    try:
        stmt = select(Disruption).where(Disruption.id == disruption_id)
        disruption = db.execute(stmt).scalar_one_or_none()
        
        if disruption is None:
            return {"error": "Disruption not found", "disruption_id": disruption_id}
        
        return {
            "id": disruption.id,
            "type": disruption.type,
            "severity": disruption.severity,
            "timestamp": ensure_iso8601(disruption.timestamp),
            "details": json_loads(disruption.details_json),
            "status": disruption.status,
        }
    finally:
        db.close()


@tool
def read_substitutions(skus: list[str]) -> list[dict]:
    """
    Read substitution options for a list of SKUs.
    
    Args:
        skus: List of SKU identifiers
        
    Returns:
        List of substitution records.
    """
    db = SessionLocal()
    try:
        stmt = select(Substitution).where(Substitution.sku.in_(skus))
        substitutions = db.execute(stmt).scalars().all()
        
        return [
            {
                "sub_id": sub.sub_id,
                "sku": sub.sku,
                "substitute_sku": sub.substitute_sku,
                "penalty_cost": sub.penalty_cost,
            }
            for sub in substitutions
        ]
    finally:
        db.close()


@tool
def update_scenario_scores(scenario_scores: list[dict]) -> dict:
    """
    Update score_json for multiple scenarios.
    
    Args:
        scenario_scores: List of dicts with scenario_id and score_json
        
    Returns:
        Dictionary with count of updated scenarios.
    """
    db = SessionLocal()
    try:
        updated_count = 0
        for item in scenario_scores:
            if "scenario_id" not in item or "score_json" not in item:
                continue
            
            stmt = select(Scenario).where(Scenario.scenario_id == item["scenario_id"])
            scenario = db.execute(stmt).scalar_one_or_none()
            
            if scenario:
                scenario.score_json = json_dumps(item["score_json"])
                updated_count += 1
        
        db.commit()
        return {"updated": updated_count}
    except Exception as e:
        db.rollback()
        return {"updated": 0, "error": str(e)}
    finally:
        db.close()


@tool
def create_pipeline_run(pipeline_run_id: str, disruption_id: str) -> dict:
    """
    Create a new pipeline run record.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        disruption_id: Associated disruption ID
        
    Returns:
        Dictionary with creation status.
    """
    db = SessionLocal()
    try:
        run = PipelineRun(
            pipeline_run_id=pipeline_run_id,
            disruption_id=disruption_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        return {"ok": True, "pipeline_run_id": pipeline_run_id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


@tool
def update_pipeline_run(pipeline_run_id: str, updates: dict) -> dict:
    """
    Update a pipeline run with status, summary, or error.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        updates: Dict with keys: status, final_summary_json, error_message, completed_at
        
    Returns:
        Dictionary with update status.
    """
    db = SessionLocal()
    try:
        stmt = select(PipelineRun).where(PipelineRun.pipeline_run_id == pipeline_run_id)
        run = db.execute(stmt).scalar_one_or_none()
        
        if run is None:
            return {"ok": False, "error": "Pipeline run not found"}
        
        if "status" in updates:
            run.status = updates["status"]
        if "final_summary_json" in updates:
            run.final_summary_json = json_dumps(updates["final_summary_json"])
        if "error_message" in updates:
            run.error_message = updates["error_message"]
        if "completed_at" in updates:
            run.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        return {"ok": True, "pipeline_run_id": pipeline_run_id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()


@tool
def write_decision_log(entry: dict) -> dict:
    """
    Write a decision log entry.
    
    Args:
        entry: Dictionary with required decision log fields
        
    Returns:
        Dictionary with operation status and log_id.
    """
    db = SessionLocal()
    try:
        # Validate required keys
        required_keys = [
            "timestamp", "pipeline_run_id", "agent_name", "input_summary",
            "output_summary", "confidence_score", "rationale", "human_decision"
        ]
        if not all(k in entry for k in required_keys):
            missing = [k for k in required_keys if k not in entry]
            return {"ok": False, "error": f"Missing required keys: {missing}"}
        
        log_id = str(uuid.uuid4())
        log_entry = DecisionLog(
            log_id=log_id,
            timestamp=ensure_iso8601(entry["timestamp"]),
            pipeline_run_id=entry["pipeline_run_id"],
            agent_name=entry["agent_name"],
            input_summary=entry["input_summary"],
            output_summary=entry["output_summary"],
            confidence_score=float(entry["confidence_score"]),
            rationale=entry["rationale"],
            human_decision=entry["human_decision"],
            approver_id=entry.get("approver_id"),
            approver_note=entry.get("approver_note"),
            override_value=json_dumps(entry["override_value"]) if entry.get("override_value") else None,
        )
        db.add(log_entry)
        db.commit()
        
        return {"ok": True, "log_id": log_id}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()
