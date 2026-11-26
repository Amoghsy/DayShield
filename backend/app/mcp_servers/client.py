"""ADK McpToolset factory for connecting DayShield agents to the FastMCP server."""

from __future__ import annotations

import sys
from pathlib import Path

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

BACKEND_ROOT = str(Path(__file__).resolve().parents[2])


def create_dayshield_mcp_toolset(tool_filter: list[str] | None = None) -> McpToolset:
    """Create an ADK McpToolset connected to the DayShield FastMCP server over stdio.

    Args:
        tool_filter: Optional list of MCP tool names to expose to the agent.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_servers.server"],
        cwd=BACKEND_ROOT,
    )
    return McpToolset(
        connection_params=StdioConnectionParams(server_params=server_params, timeout=10.0),
        tool_filter=tool_filter,
    )
