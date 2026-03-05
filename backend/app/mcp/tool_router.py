"""
Tool Router - Single choke point for MCP/local tool switching.

When USE_MCP_SERVER=1 is set, tool calls go through the MCP client.
Otherwise, they call the local tool implementations directly.

This allows agents to remain agnostic to the underlying transport.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _use_mcp() -> bool:
    """Check if MCP server mode is enabled."""
    return os.getenv("USE_MCP_SERVER", "0") == "1"


def read_disruption(disruption_id: str) -> dict[str, Any]:
    """
    Read a disruption by ID.
    
    Args:
        disruption_id: Disruption identifier
        
    Returns:
        Disruption data dictionary
    """
    if _use_mcp():
        logger.debug(f"[MCP] read_disruption: {disruption_id}")
        from app.mcp_client.client import read_disruption as mcp_read_disruption
        return mcp_read_disruption(disruption_id)
    else:
        from app.mcp.tools import read_disruption as local_read_disruption
        return local_read_disruption.invoke({"disruption_id": disruption_id})


def read_open_orders() -> list[dict[str, Any]]:
    """
    Read all open orders with their line items.
    
    Returns:
        List of order dictionaries
    """
    if _use_mcp():
        logger.debug("[MCP] read_open_orders")
        from app.mcp_client.client import read_open_orders as mcp_read_open_orders
        return mcp_read_open_orders()
    else:
        from app.mcp.tools import read_open_orders as local_read_open_orders
        return local_read_open_orders.invoke({})


def write_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Insert new scenario records into the database.
    
    Args:
        scenarios: List of scenario dictionaries
        
    Returns:
        Dictionary with count of created scenarios
    """
    if _use_mcp():
        logger.debug(f"[MCP] write_scenarios: {len(scenarios)} scenarios")
        from app.mcp_client.client import write_scenarios as mcp_write_scenarios
        return mcp_write_scenarios(scenarios)
    else:
        from app.mcp.tools import write_scenarios as local_write_scenarios
        return local_write_scenarios.invoke({"scenarios": scenarios})


def write_decision_log(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Write a decision log entry.
    
    Args:
        entry: Decision log entry dictionary
        
    Returns:
        Dictionary with operation status and log_id
    """
    if _use_mcp():
        logger.debug(f"[MCP] write_decision_log: {entry.get('agent_name')}")
        from app.mcp_client.client import write_decision_log as mcp_write_decision_log
        return mcp_write_decision_log(entry)
    else:
        from app.mcp.tools import write_decision_log as local_write_decision_log
        return local_write_decision_log.invoke({"entry": entry})


def read_inventory(dc: str, sku: str) -> dict[str, Any]:
    """
    Read inventory information for a specific DC and SKU.
    
    Args:
        dc: Distribution center identifier
        sku: Stock keeping unit identifier
        
    Returns:
        Inventory data dictionary
    """
    if _use_mcp():
        logger.debug(f"[MCP] read_inventory: {dc}/{sku}")
        from app.mcp_client.client import read_inventory as mcp_read_inventory
        return mcp_read_inventory(dc, sku)
    else:
        from app.mcp.tools import read_inventory as local_read_inventory
        return local_read_inventory.invoke({"dc": dc, "sku": sku})


def read_capacity(process: str) -> list[dict[str, Any]]:
    """
    Read capacity information for a process across all DCs.
    
    Args:
        process: Process name (e.g., 'picking', 'packing', 'shipping')
        
    Returns:
        List of capacity records
    """
    if _use_mcp():
        logger.debug(f"[MCP] read_capacity: {process}")
        from app.mcp_client.client import read_capacity as mcp_read_capacity
        return mcp_read_capacity(process)
    else:
        from app.mcp.tools import read_capacity as local_read_capacity
        return local_read_capacity.invoke({"process": process})


def read_substitutions(skus: list[str]) -> list[dict[str, Any]]:
    """
    Read substitution options for a list of SKUs.
    
    Args:
        skus: List of SKU identifiers
        
    Returns:
        List of substitution records
    """
    if _use_mcp():
        logger.debug(f"[MCP] read_substitutions: {len(skus)} SKUs")
        from app.mcp_client.client import read_substitutions as mcp_read_substitutions
        return mcp_read_substitutions(skus)
    else:
        from app.mcp.tools import read_substitutions as local_read_substitutions
        return local_read_substitutions.invoke({"skus": skus})


def update_scenario_scores(scenario_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Update score_json for multiple scenarios.
    
    Args:
        scenario_scores: List of dicts with scenario_id and score_json
        
    Returns:
        Dictionary with count of updated scenarios
    """
    if _use_mcp():
        logger.debug(f"[MCP] update_scenario_scores: {len(scenario_scores)} scores")
        from app.mcp_client.client import update_scenario_scores as mcp_update_scenario_scores
        return mcp_update_scenario_scores(scenario_scores)
    else:
        from app.mcp.tools import update_scenario_scores as local_update_scenario_scores
        return local_update_scenario_scores.invoke({"scenario_scores": scenario_scores})


def update_pipeline_run(pipeline_run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Update a pipeline run with status, summary, or error.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        updates: Dict with keys: status, final_summary_json, error_message, completed_at
        
    Returns:
        Dictionary with update status
    """
    # Note: This is always local since it's internal infrastructure
    from app.mcp.tools import update_pipeline_run as local_update_pipeline_run
    return local_update_pipeline_run.invoke({
        "pipeline_run_id": pipeline_run_id,
        "updates": updates,
    })


def create_pipeline_run(pipeline_run_id: str, disruption_id: str) -> dict[str, Any]:
    """
    Create a new pipeline run record.
    
    Args:
        pipeline_run_id: Pipeline run identifier
        disruption_id: Associated disruption ID
        
    Returns:
        Dictionary with creation status
    """
    # Note: This is always local since it's internal infrastructure
    from app.mcp.tools import create_pipeline_run as local_create_pipeline_run
    return local_create_pipeline_run.invoke({
        "pipeline_run_id": pipeline_run_id,
        "disruption_id": disruption_id,
    })
