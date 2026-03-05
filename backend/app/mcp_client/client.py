"""
MCP Client wrapper for tool invocation.

Provides a simple interface to call MCP server tools,
with connection management and typed helpers.
"""
import asyncio
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global client session (lazy initialized)
_client_session: Optional["MCPClientSession"] = None


class MCPClientSession:
    """
    MCP Client session that manages connection to MCP server.
    """
    
    def __init__(self, transport: str = "stdio"):
        """
        Initialize MCP client session.
        
        Args:
            transport: Transport type ("stdio" or "sse")
        """
        self.transport = transport
        self._client = None
        self._read_stream = None
        self._write_stream = None
        self._session = None
        self._connected = False
    
    async def connect(self):
        """Connect to the MCP server."""
        if self._connected:
            return
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise ImportError("MCP package not installed. Install with: pip install mcp")
        
        if self.transport == "stdio":
            # Start the MCP server as a subprocess
            server_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "scripts",
                "run_mcp_server.py"
            )
            
            server_params = StdioServerParameters(
                command="python",
                args=[server_script],
                env={
                    **os.environ,
                    "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                },
            )
            
            self._client = stdio_client(server_params)
            self._read_stream, self._write_stream = await self._client.__aenter__()
            
            self._session = ClientSession(self._read_stream, self._write_stream)
            await self._session.__aenter__()
            await self._session.initialize()
            
            self._connected = True
            logger.info("MCP client connected via stdio")
        else:
            raise NotImplementedError(f"Transport {self.transport} not yet implemented")
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if not self._connected:
            return
        
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
            if self._client:
                await self._client.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error disconnecting MCP client: {e}")
        finally:
            self._connected = False
    
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result (parsed from JSON)
        """
        if not self._connected:
            await self.connect()
        
        try:
            result = await self._session.call_tool(name, arguments)
            
            # Parse result content
            if result.content and len(result.content) > 0:
                text_content = result.content[0]
                if hasattr(text_content, 'text'):
                    return json.loads(text_content.text)
            
            return {"error": "No content in response"}
        except Exception as e:
            logger.exception(f"MCP tool call failed: {name}")
            return {"error": str(e)}


def get_client_session() -> MCPClientSession:
    """
    Get or create the global MCP client session.
    
    Returns:
        MCPClientSession instance
    """
    global _client_session
    
    if _client_session is None:
        transport = os.getenv("MCP_CLIENT_TRANSPORT", "stdio")
        _client_session = MCPClientSession(transport=transport)
    
    return _client_session


async def call_tool_async(name: str, arguments: dict[str, Any]) -> Any:
    """
    Call an MCP tool asynchronously.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    session = get_client_session()
    return await session.call_tool(name, arguments)


def call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """
    Call an MCP tool synchronously.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(call_tool_async(name, arguments))


# Typed helper functions for common tools
def read_disruption(disruption_id: str) -> dict[str, Any]:
    """Read a disruption by ID via MCP."""
    return call_tool("read_disruption", {"disruption_id": disruption_id})


def read_open_orders() -> list[dict[str, Any]]:
    """Read all open orders via MCP."""
    return call_tool("read_open_orders", {})


def write_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    """Write scenarios via MCP."""
    return call_tool("write_scenarios", {"scenarios": scenarios})


def write_decision_log(entry: dict[str, Any]) -> dict[str, Any]:
    """Write a decision log entry via MCP."""
    return call_tool("write_decision_log", {"entry": entry})


def read_inventory(dc: str, sku: str) -> dict[str, Any]:
    """Read inventory for DC/SKU via MCP."""
    return call_tool("read_inventory", {"dc": dc, "sku": sku})


def read_capacity(process: str) -> list[dict[str, Any]]:
    """Read capacity for a process via MCP."""
    return call_tool("read_capacity", {"process": process})


def read_substitutions(skus: list[str]) -> list[dict[str, Any]]:
    """Read substitution options for SKUs via MCP."""
    return call_tool("read_substitutions", {"skus": skus})


def update_scenario_scores(scenario_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Update scenario scores via MCP."""
    return call_tool("update_scenario_scores", {"scenario_scores": scenario_scores})
