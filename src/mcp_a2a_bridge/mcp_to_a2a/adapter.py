"""MCPtoA2AAdapter: connect to MCP server(s) and expose as an A2A agent."""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any

import uvicorn
from fastapi import FastAPI

from mcp import ClientSession
from mcp.types import Tool as MCPTool

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
)

from mcp_a2a_bridge.common.config import BridgeConfig, MCPServerConfig
from mcp_a2a_bridge.common.transport import connect_mcp
from mcp_a2a_bridge.mcp_to_a2a.agent_card import mcp_tools_to_skills
from mcp_a2a_bridge.mcp_to_a2a.executor import MCPBridgeExecutor

logger = logging.getLogger(__name__)


class MCPtoA2AAdapter:
    """Connect to one or more MCP servers and expose them as a single A2A agent.

    Usage:
        ```python
        config = BridgeConfig.from_yaml("bridge.yaml")
        adapter = MCPtoA2AAdapter(config)
        await adapter.run()  # Starts A2A HTTP server
        ```

    Or programmatically:
        ```python
        adapter = MCPtoA2AAdapter(config)
        app = await adapter.build_app()  # Returns FastAPI app
        ```
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config
        self._exit_stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}
        self._all_tools: list[MCPTool] = []
        self._app: FastAPI | None = None

    async def _connect_servers(self) -> None:
        """Connect to all configured MCP servers and discover tools."""
        for server_config in self._config.mcp_servers:
            try:
                session = await self._exit_stack.enter_async_context(
                    connect_mcp(server_config)
                )
                self._sessions[server_config.name] = session

                # Discover tools
                result = await session.list_tools()
                for tool in result.tools:
                    self._all_tools.append(tool)

                logger.info(
                    "MCP server '%s': %d tools discovered — %s",
                    server_config.name,
                    len(result.tools),
                    [t.name for t in result.tools],
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to MCP server '%s': %s",
                    server_config.name,
                    e,
                )

        if not self._all_tools:
            logger.warning("No MCP tools discovered from any server.")

    def _build_agent_card(self) -> AgentCard:
        """Generate an A2A AgentCard from discovered MCP tools."""
        skills_data = mcp_tools_to_skills(self._all_tools)
        base_url = f"http://{self._config.a2a_host}:{self._config.a2a_port}"

        skills = [
            AgentSkill(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                tags=s["tags"],
                examples=s["examples"],
                input_modes=s["input_modes"],
                output_modes=s["output_modes"],
            )
            for s in skills_data
        ]

        return AgentCard(
            name=self._config.a2a_agent_name,
            description=self._config.a2a_agent_description,
            provider=AgentProvider(
                organization="mcp-a2a-bridge",
                url="https://github.com/naveenkumarbaskaran/mcp-a2a-bridge",
            ),
            version="0.1.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=False,
            ),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=skills,
            supported_interfaces=[
                AgentInterface(
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                    url=f"{base_url}/a2a/jsonrpc",
                ),
                AgentInterface(
                    protocol_binding="HTTP+JSON",
                    protocol_version="1.0",
                    url=f"{base_url}/a2a/rest",
                ),
            ],
        )

    def _build_executor(self) -> MCPBridgeExecutor:
        """Create the A2A executor wired to MCP sessions."""
        executor = MCPBridgeExecutor(
            mcp_sessions=self._sessions,
            mcp_tools=self._all_tools,
            llm_config=self._config.llm,
        )

        # Register tool → session mappings
        for server_config in self._config.mcp_servers:
            session = self._sessions.get(server_config.name)
            if not session:
                continue
            # Re-discover to map tools to sessions
            # (tools were already cached during _connect_servers)
            for tool in self._all_tools:
                # If tool isn't mapped yet, map it to first session that has it
                if tool.name not in executor._tool_to_session:
                    executor.register_tool_session(tool.name, session)

        return executor

    async def build_app(self) -> FastAPI:
        """Connect to MCP servers and build the FastAPI A2A application.

        Returns:
            A configured FastAPI app ready to serve A2A requests.
        """
        await self._connect_servers()

        agent_card = self._build_agent_card()
        executor = self._build_executor()
        task_store = InMemoryTaskStore()

        request_handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=task_store,
            agent_card=agent_card,
        )

        app = FastAPI(
            title=self._config.a2a_agent_name,
            description="A2A agent bridging to MCP tool servers",
            version="0.1.0",
        )

        app.routes.extend(
            create_jsonrpc_routes(
                request_handler=request_handler,
                rpc_url="/a2a/jsonrpc",
            )
        )
        app.routes.extend(
            create_rest_routes(
                request_handler=request_handler,
                path_prefix="/a2a/rest",
            )
        )
        app.routes.extend(create_agent_card_routes(agent_card=agent_card))

        # Health endpoint
        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {
                "status": "ok",
                "bridge": "mcp-a2a",
                "mcp_servers": list(self._sessions.keys()),
                "tools": [t.name for t in self._all_tools],
                "tool_count": len(self._all_tools),
            }

        self._app = app
        logger.info(
            "A2A agent ready: %s (%d tools from %d MCP servers)",
            self._config.a2a_agent_name,
            len(self._all_tools),
            len(self._sessions),
        )
        return app

    async def run(self) -> None:
        """Start the A2A HTTP server (blocking).

        Connects to all MCP servers, builds the agent, and starts serving.
        """
        async with self._exit_stack:
            app = await self.build_app()

            config = uvicorn.Config(
                app=app,
                host=self._config.a2a_host,
                port=self._config.a2a_port,
                log_level=self._config.log_level.lower(),
            )
            server = uvicorn.Server(config)
            await server.serve()

    async def close(self) -> None:
        """Shutdown all MCP connections."""
        await self._exit_stack.aclose()
