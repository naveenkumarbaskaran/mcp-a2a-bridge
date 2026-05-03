"""mcp-a2a-bridge: Bidirectional bridge between MCP and A2A protocols."""

__version__ = "0.1.0"

from mcp_a2a_bridge.a2a_to_mcp.adapter import A2AtoMCPAdapter
from mcp_a2a_bridge.mcp_to_a2a.adapter import MCPtoA2AAdapter

__all__ = ["MCPtoA2AAdapter", "A2AtoMCPAdapter"]
