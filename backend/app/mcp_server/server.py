"""
MCP Server for disruption response planner.

Exposes database operations as MCP tools via stdio or SSE transport.
"""
import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def create_mcp_server():
    """
    Create and configure the MCP server with registered tools.
    
    Returns:
        Configured MCP server instance
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        raise ImportError(
            "MCP package not installed. Install with: pip install mcp"
        )
    
    # Import local tool implementations
    from app.mcp.tools import (
        read_disruption as _read_disruption,
        read_open_orders as _read_open_orders,
        read_inbound_status as _read_inbound_status,
        write_scenarios as _write_scenarios,
        write_decision_log as _write_decision_log,
        read_inventory as _read_inventory,
        read_capacity as _read_capacity,
        read_substitutions as _read_substitutions,
        update_scenario_scores as _update_scenario_scores,
    )
    
    server = Server("disruption-response-planner")
    
    # Define MCP tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="read_disruption",
                description="Read a specific disruption by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "disruption_id": {
                            "type": "string",
                            "description": "Disruption identifier"
                        }
                    },
                    "required": ["disruption_id"]
                }
            ),
            Tool(
                name="read_open_orders",
                description="Read all open orders with their line items",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="read_inbound_status",
                description="Read inbound shipment status for a truck",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "truck_id": {
                            "type": "string",
                            "description": "Truck identifier"
                        }
                    },
                    "required": ["truck_id"]
                }
            ),
            Tool(
                name="write_scenarios",
                description="Insert new scenario records into the database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scenarios": {
                            "type": "array",
                            "description": "List of scenario dictionaries",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "disruption_id": {"type": "string"},
                                    "order_id": {"type": "string"},
                                    "action_type": {"type": "string"},
                                    "plan_json": {"type": "object"}
                                },
                                "required": ["disruption_id", "order_id", "action_type", "plan_json"]
                            }
                        }
                    },
                    "required": ["scenarios"]
                }
            ),
            Tool(
                name="write_decision_log",
                description="Write a decision log entry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entry": {
                            "type": "object",
                            "description": "Decision log entry with required fields",
                            "properties": {
                                "timestamp": {"type": "string"},
                                "pipeline_run_id": {"type": "string"},
                                "agent_name": {"type": "string"},
                                "input_summary": {"type": "string"},
                                "output_summary": {"type": "string"},
                                "confidence_score": {"type": "number"},
                                "rationale": {"type": "string"},
                                "human_decision": {"type": "string"}
                            },
                            "required": [
                                "timestamp", "pipeline_run_id", "agent_name",
                                "input_summary", "output_summary", "confidence_score",
                                "rationale", "human_decision"
                            ]
                        }
                    },
                    "required": ["entry"]
                }
            ),
            Tool(
                name="read_inventory",
                description="Read inventory information for a specific DC and SKU",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dc": {
                            "type": "string",
                            "description": "Distribution center identifier"
                        },
                        "sku": {
                            "type": "string",
                            "description": "Stock keeping unit identifier"
                        }
                    },
                    "required": ["dc", "sku"]
                }
            ),
            Tool(
                name="read_capacity",
                description="Read capacity information for a process",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "process": {
                            "type": "string",
                            "description": "Process name (picking, packing, shipping)"
                        }
                    },
                    "required": ["process"]
                }
            ),
            Tool(
                name="read_substitutions",
                description="Read substitution options for SKUs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "skus": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of SKU identifiers"
                        }
                    },
                    "required": ["skus"]
                }
            ),
            Tool(
                name="update_scenario_scores",
                description="Update scores for multiple scenarios",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scenario_scores": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "scenario_id": {"type": "string"},
                                    "score_json": {"type": "object"}
                                },
                                "required": ["scenario_id", "score_json"]
                            }
                        }
                    },
                    "required": ["scenario_scores"]
                }
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute a tool and return results."""
        try:
            if name == "read_disruption":
                result = _read_disruption.invoke({"disruption_id": arguments["disruption_id"]})
            elif name == "read_open_orders":
                result = _read_open_orders.invoke({})
            elif name == "read_inbound_status":
                result = _read_inbound_status.invoke({"truck_id": arguments["truck_id"]})
            elif name == "write_scenarios":
                result = _write_scenarios.invoke({"scenarios": arguments["scenarios"]})
            elif name == "write_decision_log":
                result = _write_decision_log.invoke({"entry": arguments["entry"]})
            elif name == "read_inventory":
                result = _read_inventory.invoke({"dc": arguments["dc"], "sku": arguments["sku"]})
            elif name == "read_capacity":
                result = _read_capacity.invoke({"process": arguments["process"]})
            elif name == "read_substitutions":
                result = _read_substitutions.invoke({"skus": arguments["skus"]})
            elif name == "update_scenario_scores":
                result = _update_scenario_scores.invoke({"scenario_scores": arguments["scenario_scores"]})
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        except Exception as e:
            logger.exception(f"Tool {name} failed")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
    
    return server


async def run_stdio_server():
    """Run the MCP server via stdio transport."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError:
        raise ImportError("MCP package not installed. Install with: pip install mcp")
    
    server = create_mcp_server()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_sse_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the MCP server via SSE transport."""
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn
    except ImportError:
        raise ImportError(
            "MCP or Starlette not installed. Install with: pip install mcp starlette uvicorn"
        )
    
    server = create_mcp_server()
    sse = SseServerTransport("/messages")
    
    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
    
    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)
    
    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ]
    )
    
    config = uvicorn.Config(app, host=host, port=port)
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


def main():
    """Main entry point for MCP server."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport == "sse":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8001"))
        logger.info(f"Starting MCP server via SSE on {host}:{port}")
        asyncio.run(run_sse_server(host, port))
    else:
        logger.info("Starting MCP server via stdio")
        asyncio.run(run_stdio_server())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
