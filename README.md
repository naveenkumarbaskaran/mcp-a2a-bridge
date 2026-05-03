<div align="center">

# mcp-a2a-bridge

**Bidirectional bridge between MCP and A2A protocols**

Connect any [MCP](https://modelcontextprotocol.io/) tool server to the [A2A](https://github.com/a2aproject/a2a-python) agent ecosystem — and vice versa.

[![PyPI version](https://img.shields.io/pypi/v/mcp-a2a-bridge?color=blue)](https://pypi.org/project/mcp-a2a-bridge/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-a2a-bridge)](https://pypi.org/project/mcp-a2a-bridge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## The Problem

**MCP** (Model Context Protocol) and **A2A** (Agent-to-Agent) are the two dominant agent protocols in 2026 — but they don't talk to each other.

- You have MCP tool servers but need them accessible as A2A agents
- You have A2A agents but need them usable from Claude Desktop or other MCP clients
- You want to mix and match tools from both ecosystems

## The Solution

`mcp-a2a-bridge` provides **bidirectional** bridging with a single config file:

```
┌─────────────────┐                        ┌─────────────────┐
│   MCP Servers    │ ──── MCP → A2A ────▶  │   A2A Clients   │
│  (tool servers)  │                        │ (Joule, agents) │
└─────────────────┘                        └─────────────────┘

┌─────────────────┐                        ┌─────────────────┐
│   A2A Agents     │ ──── A2A → MCP ────▶  │   MCP Clients   │
│ (smart agents)   │                        │ (Claude Desktop) │
└─────────────────┘                        └─────────────────┘
```

## Quick Start

### Install

```bash
pip install mcp-a2a-bridge
```

### MCP → A2A (one command)

Turn any MCP server into an A2A agent:

```bash
# Expose a local MCP server as an A2A agent on port 8000
mcp-a2a-bridge quick python -m my_mcp_server --port 8000

# Check it works
curl http://localhost:8000/.well-known/agent-card.json
curl http://localhost:8000/health
```

### A2A → MCP (one command)

Turn any A2A agent into MCP tools:

```bash
# Expose an A2A agent as MCP tools
mcp-a2a-bridge expose https://my-agent.example.com --port 9000
```

Then add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "agent-bridge": {
      "url": "http://127.0.0.1:9000/mcp"
    }
  }
}
```

### Config File (advanced)

For multi-server setups, create a `bridge.yaml`:

```yaml
# Connect to multiple MCP servers
mcp_servers:
  - name: my-tools
    transport: stdio
    command: python
    args: ["-m", "my_mcp_server"]

  - name: remote-tools
    transport: streamable-http
    url: http://localhost:3000/mcp

# Expose as a single A2A agent
a2a_agent_name: "Multi-Tool Agent"
a2a_port: 8000

# Also bridge A2A agents to MCP
a2a_agents:
  - name: order-analyst
    url: https://my-agent.example.com

mcp_port: 9000

# LLM for routing natural language → tool calls
llm:
  model: gpt-4o-mini
```

```bash
mcp-a2a-bridge serve --config bridge.yaml
```

## How It Works

### MCP → A2A Direction

1. Connects to configured MCP server(s) and discovers all tools
2. Auto-generates an A2A `AgentCard` with skills derived from MCP tools
3. When an A2A request arrives (natural language), uses an LLM to:
   - Parse the query
   - Select the right MCP tool(s)
   - Format arguments
   - Call the tool(s) via MCP
4. Returns results as A2A artifacts with full task lifecycle

### A2A → MCP Direction

1. Fetches `AgentCard` from configured A2A agent(s)
2. Generates MCP tools from agent skills (one tool per skill)
3. When an MCP `call_tool` arrives, forwards as an A2A `message/send`
4. Returns the agent's response as MCP `TextContent`

## Python API

For programmatic use:

```python
import asyncio
from mcp_a2a_bridge import MCPtoA2AAdapter, A2AtoMCPAdapter
from mcp_a2a_bridge.common.config import BridgeConfig

# MCP → A2A
config = BridgeConfig.from_yaml("bridge.yaml")
adapter = MCPtoA2AAdapter(config)
app = await adapter.build_app()  # Returns FastAPI app

# A2A → MCP
adapter = A2AtoMCPAdapter(config)
mcp_server = await adapter.build_server()  # Returns FastMCP server
```

## Architecture

```
src/mcp_a2a_bridge/
├── cli.py                  # Click CLI (serve, quick, expose)
├── common/
│   ├── config.py           # YAML config loader (BridgeConfig)
│   └── transport.py        # MCP transport helpers (stdio/SSE/HTTP)
├── mcp_to_a2a/
│   ├── adapter.py          # MCPtoA2AAdapter (main orchestrator)
│   ├── agent_card.py       # Auto-generate AgentCard from MCP tools
│   ├── executor.py         # A2A AgentExecutor → MCP tool calls
│   └── tool_router.py      # LLM-based natural language → tool routing
└── a2a_to_mcp/
    ├── adapter.py           # A2AtoMCPAdapter (main orchestrator)
    └── tool_factory.py      # Generate MCP tools from A2A skills
```

## Supported Transports

| Protocol | Transport | Status |
|----------|-----------|--------|
| MCP | stdio (local subprocess) | ✅ |
| MCP | SSE (HTTP) | ✅ |
| MCP | Streamable HTTP | ✅ |
| A2A | JSON-RPC | ✅ |
| A2A | REST (HTTP+JSON) | ✅ |
| A2A | gRPC | 🔄 (install `mcp-a2a-bridge[grpc]`) |

## LLM Support

The MCP → A2A direction uses [litellm](https://github.com/BerriAI/litellm) for routing, so any LLM works:

```yaml
llm:
  model: gpt-4o-mini          # OpenAI
  # model: claude-sonnet-4-20250514  # Anthropic
  # model: gemini/gemini-2.5-pro    # Google
  # model: ollama/llama3           # Local via Ollama
```

Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. as environment variables, or pass `api_key` in config.

## Contributing

```bash
git clone https://github.com/naveenkumarbaskaran/mcp-a2a-bridge.git
cd mcp-a2a-bridge
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

## Author

**Naveen Kumar Baskaran** — [GitHub](https://github.com/naveenkumarbaskaran) · [LinkedIn](https://www.linkedin.com/in/naveenkumarbaskaran/)

---

<div align="center">

*The answer to "MCP vs A2A" is "both."*

</div>
