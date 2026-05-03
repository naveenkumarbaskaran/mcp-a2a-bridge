"""A2AtoMCPAdapter: connect to A2A agent(s) and expose them as an MCP server."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from mcp_a2a_bridge.a2a_to_mcp.tool_factory import agent_card_to_mcp_tools
from mcp_a2a_bridge.common.config import A2AAgentConfig, BridgeConfig

logger = logging.getLogger(__name__)


class A2AtoMCPAdapter:
    """Connect to one or more A2A agents and expose their skills as MCP tools.

    Usage:
        ```python
        config = BridgeConfig.from_yaml("bridge.yaml")
        adapter = A2AtoMCPAdapter(config)
        await adapter.run()  # Starts MCP server
        ```

    Or get the FastMCP server for custom use:
        ```python
        adapter = A2AtoMCPAdapter(config)
        mcp_server = await adapter.build_server()
        ```
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config
        self._mcp: FastMCP | None = None
        self._agent_cards: dict[str, dict[str, Any]] = {}  # url → card
        self._tool_registry: dict[str, dict[str, Any]] = {}  # tool_name → tool_def

    async def _discover_agents(self) -> None:
        """Fetch agent cards from all configured A2A agents."""
        async with httpx.AsyncClient(timeout=10) as client:
            for agent_config in self._config.a2a_agents:
                try:
                    # Try standard discovery endpoint
                    card_url = f"{agent_config.url.rstrip('/')}/.well-known/agent-card.json"
                    response = await client.get(
                        card_url,
                        headers=agent_config.headers,
                    )
                    response.raise_for_status()
                    card = response.json()
                    self._agent_cards[agent_config.url] = card

                    logger.info(
                        "Discovered A2A agent '%s' at %s (%d skills)",
                        card.get("name", "unknown"),
                        agent_config.url,
                        len(card.get("skills", [])),
                    )
                except Exception as e:
                    logger.error(
                        "Failed to discover A2A agent at '%s': %s",
                        agent_config.url,
                        e,
                    )

    async def _call_a2a_agent(
        self,
        agent_url: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Send a message to an A2A agent and return the text response.

        Uses the REST interface (message/send) for simplicity.

        Args:
            agent_url: Base URL of the A2A agent.
            message: Natural language message to send.
            headers: Optional HTTP headers (auth, etc.).

        Returns:
            The agent's text response.
        """
        import uuid

        send_url = f"{agent_url.rstrip('/')}/a2a/rest/message/send"

        payload = {
            "message": {
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [{"text": message}],
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                send_url,
                json=payload,
                headers=headers or {},
            )
            response.raise_for_status()
            data = response.json()

        # Extract text from response
        return self._extract_text(data)

    def _extract_text(self, response: dict[str, Any]) -> str:
        """Extract readable text from an A2A response (task or message)."""
        # Check for artifacts in task response
        if "artifacts" in response:
            texts = []
            for artifact in response["artifacts"]:
                for part in artifact.get("parts", []):
                    if "text" in part:
                        texts.append(part["text"])
            if texts:
                return "\n".join(texts)

        # Check for message in result
        result = response.get("result", response)
        if isinstance(result, dict):
            status = result.get("status", {})
            msg = status.get("message", {})
            parts = msg.get("parts", [])
            texts = [p["text"] for p in parts if "text" in p]
            if texts:
                return "\n".join(texts)

        # Check for direct parts
        parts = response.get("parts", [])
        texts = [p["text"] for p in parts if isinstance(p, dict) and "text" in p]
        if texts:
            return "\n".join(texts)

        return json.dumps(response, indent=2)

    async def build_server(self) -> FastMCP:
        """Discover A2A agents and build a FastMCP server with bridged tools.

        Returns:
            A configured FastMCP server ready to run.
        """
        await self._discover_agents()

        self._mcp = FastMCP(
            name=self._config.mcp_server_name,
            instructions=(
                "This MCP server bridges to A2A agents. "
                "Each tool corresponds to a skill from a connected A2A agent."
            ),
        )

        # Generate MCP tools from agent cards
        for agent_config in self._config.a2a_agents:
            card = self._agent_cards.get(agent_config.url)
            if not card:
                continue

            tools = agent_card_to_mcp_tools(card, agent_config.url)
            for tool_def in tools:
                self._tool_registry[tool_def["name"]] = tool_def
                self._register_mcp_tool(tool_def, agent_config)

        logger.info(
            "MCP server ready: %s (%d tools from %d A2A agents)",
            self._config.mcp_server_name,
            len(self._tool_registry),
            len(self._agent_cards),
        )
        return self._mcp

    def _register_mcp_tool(
        self,
        tool_def: dict[str, Any],
        agent_config: A2AAgentConfig,
    ) -> None:
        """Register a single MCP tool backed by an A2A agent call."""
        assert self._mcp is not None

        agent_url = tool_def["_agent_url"]
        tool_name = tool_def["name"]
        description = tool_def["description"]
        headers = agent_config.headers

        # Closure over agent_url and headers
        @self._mcp.tool(name=tool_name, description=description)
        async def bridged_tool(message: str) -> str:
            """Forward the message to the A2A agent and return the response."""
            try:
                result = await self._call_a2a_agent(
                    agent_url=agent_url,
                    message=message,
                    headers=headers,
                )
                return result
            except Exception as e:
                logger.error("A2A call failed for tool '%s': %s", tool_name, e)
                return f"Error calling A2A agent: {e}"

    async def run(self) -> None:
        """Build and start the MCP server (blocking)."""
        mcp = await self.build_server()
        mcp.settings.host = self._config.mcp_host
        mcp.settings.port = self._config.mcp_port
        mcp.run(transport=self._config.mcp_transport)
