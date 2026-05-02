"""Example: Expose a local MCP tool server as an A2A agent.

This creates a simple MCP server with two tools, then bridges it
to A2A so it can be called by any A2A client.

Usage:
    python examples/mcp_to_a2a_basic.py
    # Then: curl http://localhost:8000/.well-known/agent-card.json
"""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp_a2a_bridge import MCPtoA2AAdapter
from mcp_a2a_bridge.common.config import BridgeConfig


# Step 1: Create a tiny MCP server inline (saved to a temp file)
MCP_SERVER_CODE = '''
from mcp.server.fastmcp import FastMCP
import datetime

mcp = FastMCP("Demo Tools")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! Welcome to the MCP-A2A bridge demo."

@mcp.tool()
def current_time() -> str:
    """Get the current date and time."""
    return datetime.datetime.now().isoformat()

@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # Only allow safe math operations
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "Error: Only basic math operations are allowed."
        result = eval(expression)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
'''


async def main():
    # Write the demo MCP server to a temp file
    server_file = Path(tempfile.mktemp(suffix=".py"))
    server_file.write_text(MCP_SERVER_CODE)

    try:
        # Configure the bridge
        config = BridgeConfig.from_dict({
            "mcp_servers": [
                {
                    "name": "demo-tools",
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(server_file)],
                }
            ],
            "a2a_agent_name": "Demo Bridge Agent",
            "a2a_agent_description": (
                "A demo agent that can greet people, tell the time, "
                "and calculate math expressions."
            ),
            "a2a_port": 8000,
            "llm": {
                "model": "gpt-4o-mini",
                "temperature": 0.0,
            },
            "log_level": "INFO",
        })

        print("=" * 60)
        print("MCP → A2A Bridge Demo")
        print("=" * 60)
        print()
        print("Starting A2A agent on http://localhost:8000")
        print()
        print("Endpoints:")
        print("  Agent Card:  http://localhost:8000/.well-known/agent-card.json")
        print("  JSON-RPC:    http://localhost:8000/a2a/jsonrpc")
        print("  REST:        http://localhost:8000/a2a/rest/message/send")
        print("  Health:      http://localhost:8000/health")
        print()
        print("Try:")
        print('  curl -s http://localhost:8000/health | python -m json.tool')
        print()

        adapter = MCPtoA2AAdapter(config)
        await adapter.run()

    finally:
        server_file.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
