#!/usr/bin/env python
"""
MCP Server runner script.

Usage:
    # Run via stdio (default)
    python scripts/run_mcp_server.py
    
    # Run via SSE transport
    MCP_TRANSPORT=sse python scripts/run_mcp_server.py
    
    # Run via SSE on custom port
    MCP_TRANSPORT=sse MCP_PORT=8001 python scripts/run_mcp_server.py
"""
import logging
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mcp_server.server import main

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
