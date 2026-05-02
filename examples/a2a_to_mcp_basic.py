"""Example: Expose an A2A agent as MCP tools.

Given any running A2A agent, this discovers its skills and creates
MCP tools so it can be used from Claude Desktop or any MCP client.

Usage:
    # First, have an A2A agent running:
    #   python examples/mcp_to_a2a_basic.py  (port 8000)

    # Then expose it as MCP:
    python examples/a2a_to_mcp_basic.py
"""

import asyncio

from mcp_a2a_bridge import A2AtoMCPAdapter
from mcp_a2a_bridge.common.config import BridgeConfig


async def main():
    config = BridgeConfig.from_dict({
        "a2a_agents": [
            {
                "name": "demo-agent",
                "url": "http://localhost:8000",
                "description": "Demo bridge agent from the MCP→A2A example",
            }
        ],
        "mcp_server_name": "A2A Agent Tools",
        "mcp_transport": "streamable-http",
        "mcp_host": "127.0.0.1",
        "mcp_port": 9000,
        "log_level": "INFO",
    })

    print("=" * 60)
    print("A2A → MCP Bridge Demo")
    print("=" * 60)
    print()
    print("Connecting to A2A agent at http://localhost:8000...")
    print("MCP server will start on http://127.0.0.1:9000")
    print()
    print("Add to Claude Desktop config (claude_desktop_config.json):")
    print('  {')
    print('    "mcpServers": {')
    print('      "a2a-bridge": {')
    print('        "url": "http://127.0.0.1:9000/mcp"')
    print('      }')
    print('    }')
    print('  }')
    print()

    adapter = A2AtoMCPAdapter(config)
    await adapter.run()


if __name__ == "__main__":
    asyncio.run(main())
