"""
Tool Router - Single choke point for MCP/local tool switching.

When USE_MCP_SERVER=1 (default), tool calls go through the MCP client.
Otherwise, they call the local tool implementations directly.
Falls back to local tools if MCP package is not installed or connection fails.

This allows agents to remain agnostic to the underlying transport.
"""
import logging
import os
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

# Cached: MCP client available (package installed and working)
_mcp_available: bool | None = None

T = TypeVar("T")


def _use_mcp() -> bool:
    """Check if MCP server mode is enabled (default: True)."""
    return os.getenv("USE_MCP_SERVER", "1") == "1"


def _try_mcp_then_local(
    mcp_fn: Callable[[], T],
    local_fn: Callable[[], T],
    tool_name: str,
) -> T:
    """
    Try MCP call first; fall back to local on ImportError or connection failure.
    """
    global _mcp_available
    if not _use_mcp():
        return local_fn()
    if _mcp_available is False:
        return local_fn()
    try:
        result = mcp_fn()
        if _mcp_available is None:
            _mcp_available = True
            logger.info("MCP client connected; tool calls routed via MCP server")
        return result
    except ImportError as e:
        if _mcp_available is None:
            _mcp_available = False
            logger.warning(
                "MCP package not installed or unavailable; falling back to local tools. "
                "Install with: pip install mcp"
            )
        return local_fn()
    except Exception as e:
        logger.warning(f"MCP call failed for {tool_name}: {e}; falling back to local")
        return local_fn()


def read_disruption(disruption_id: str) -> dict[str, Any]:
    """
    Read a disruption by ID.
    
    Args:
        disruption_id: Disruption identifier
        
    Returns:
        Disruption data dictionary
    """
    def _mcp():
        from app.mcp_client.client import read_disruption as fn
        return fn(disruption_id)

    def _local():
        from app.mcp.tools import read_disruption as fn
        return fn.invoke({"disruption_id": disruption_id})

    return _try_mcp_then_local(_mcp, _local, "read_disruption")


def read_open_orders() -> list[dict[str, Any]]:
    """
    Read all open orders with their line items.
    
    Returns:
        List of order dictionaries
    """
    def _mcp():
        from app.mcp_client.client import read_open_orders as fn
        return fn()

    def _local():
        from app.mcp.tools import read_open_orders as fn
        return fn.invoke({})

    return _try_mcp_then_local(_mcp, _local, "read_open_orders")


def read_inbound_status(truck_id: str) -> dict[str, Any]:
    """
    Read inbound shipment status for a truck.
    
    Args:
        truck_id: Truck identifier
        
    Returns:
        Truck ETA, DC, sku_list
    """
    def _mcp():
        from app.mcp_client.client import read_inbound_status as fn
        return fn(truck_id)

    def _local():
        from app.mcp.tools import read_inbound_status as fn
        return fn.invoke({"truck_id": truck_id})

    return _try_mcp_then_local(_mcp, _local, "read_inbound_status")


def write_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Insert new scenario records into the database.
    
    Args:
        scenarios: List of scenario dictionaries
        
    Returns:
        Dictionary with count of created scenarios
    """
    def _mcp():
        from app.mcp_client.client import write_scenarios as fn
        return fn(scenarios)

    def _local():
        from app.mcp.tools import write_scenarios as fn
        return fn.invoke({"scenarios": scenarios})

    return _try_mcp_then_local(_mcp, _local, "write_scenarios")


def write_decision_log(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Write a decision log entry.
    
    Args:
        entry: Decision log entry dictionary
        
    Returns:
        Dictionary with operation status and log_id
    """
    def _mcp():
        from app.mcp_client.client import write_decision_log as fn
        return fn(entry)

    def _local():
        from app.mcp.tools import write_decision_log as fn
        return fn.invoke({"entry": entry})

    return _try_mcp_then_local(_mcp, _local, "write_decision_log")


def read_inventory(dc: str, sku: str) -> dict[str, Any]:
    """
    Read inventory information for a specific DC and SKU.
    
    Args:
        dc: Distribution center identifier
        sku: Stock keeping unit identifier
        
    Returns:
        Inventory data dictionary
    """
    def _mcp():
        from app.mcp_client.client import read_inventory as fn
        return fn(dc, sku)

    def _local():
        from app.mcp.tools import read_inventory as fn
        return fn.invoke({"dc": dc, "sku": sku})

    return _try_mcp_then_local(_mcp, _local, "read_inventory")


def read_capacity(process: str) -> list[dict[str, Any]]:
    """
    Read capacity information for a process across all DCs.
    
    Args:
        process: Process name (e.g., 'picking', 'packing', 'shipping')
        
    Returns:
        List of capacity records
    """
    def _mcp():
        from app.mcp_client.client import read_capacity as fn
        return fn(process)

    def _local():
        from app.mcp.tools import read_capacity as fn
        return fn.invoke({"process": process})

    return _try_mcp_then_local(_mcp, _local, "read_capacity")


def read_substitutions(skus: list[str]) -> list[dict[str, Any]]:
    """
    Read substitution options for a list of SKUs.
    
    Args:
        skus: List of SKU identifiers
        
    Returns:
        List of substitution records
    """
    def _mcp():
        from app.mcp_client.client import read_substitutions as fn
        return fn(skus)

    def _local():
        from app.mcp.tools import read_substitutions as fn
        return fn.invoke({"skus": skus})

    return _try_mcp_then_local(_mcp, _local, "read_substitutions")


def update_scenario_scores(scenario_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Update score_json for multiple scenarios.
    
    Args:
        scenario_scores: List of dicts with scenario_id and score_json
        
    Returns:
        Dictionary with count of updated scenarios
    """
    def _mcp():
        from app.mcp_client.client import update_scenario_scores as fn
        return fn(scenario_scores)

    def _local():
        from app.mcp.tools import update_scenario_scores as fn
        return fn.invoke({"scenario_scores": scenario_scores})

    return _try_mcp_then_local(_mcp, _local, "update_scenario_scores")


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
