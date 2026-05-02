"""Transport helpers for connecting to MCP servers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from mcp_a2a_bridge.common.config import MCPServerConfig

logger = logging.getLogger(__name__)


@asynccontextmanager
async def connect_mcp(
    config: MCPServerConfig,
) -> AsyncGenerator[ClientSession, None]:
    """Connect to an MCP server using the configured transport.

    Yields a ready-to-use ClientSession with initialize() already called.

    Args:
        config: MCP server connection configuration.

    Yields:
        An initialized MCP ClientSession.

    Raises:
        ValueError: If the transport type is unknown.
    """
    transport = config.transport.lower()

    if transport == "stdio":
        if not config.command:
            raise ValueError(f"MCP server '{config.name}': stdio transport requires 'command'")
        params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("Connected to MCP server '%s' via stdio", config.name)
                yield session

    elif transport == "sse":
        if not config.url:
            raise ValueError(f"MCP server '{config.name}': SSE transport requires 'url'")
        async with sse_client(
            url=config.url,
            headers=config.headers or {},
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info("Connected to MCP server '%s' via SSE at %s", config.name, config.url)
                yield session

    elif transport in ("streamable-http", "streamable_http"):
        if not config.url:
            raise ValueError(
                f"MCP server '{config.name}': streamable-http transport requires 'url'"
            )
        async with streamable_http_client(url=config.url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                logger.info(
                    "Connected to MCP server '%s' via streamable-http at %s",
                    config.name,
                    config.url,
                )
                yield session

    else:
        raise ValueError(
            f"Unknown MCP transport '{transport}' for server '{config.name}'. "
            "Use 'stdio', 'sse', or 'streamable-http'."
        )
