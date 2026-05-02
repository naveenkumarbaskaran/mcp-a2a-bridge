"""CLI for mcp-a2a-bridge."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click

from mcp_a2a_bridge.common.config import BridgeConfig


def _setup_logging(level: str) -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )


@click.group()
@click.version_option(package_name="mcp-a2a-bridge")
def main() -> None:
    """mcp-a2a-bridge: Bidirectional bridge between MCP and A2A protocols."""
    pass


@main.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to bridge configuration YAML file.",
)
@click.option(
    "--direction",
    type=click.Choice(["mcp-to-a2a", "a2a-to-mcp", "both"]),
    default="both",
    help="Which bridge direction to run.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Override log level from config.",
)
def serve(config: Path, direction: str, log_level: str | None) -> None:
    """Start the bridge server(s).

    Connects to configured MCP servers and/or A2A agents and starts
    serving the bridge in the specified direction(s).
    """
    cfg = BridgeConfig.from_yaml(config)
    if log_level:
        cfg.log_level = log_level

    _setup_logging(cfg.log_level)
    logger = logging.getLogger("mcp_a2a_bridge")

    if direction == "mcp-to-a2a":
        if not cfg.mcp_servers:
            click.echo("Error: No mcp_servers configured. Check your config file.", err=True)
            sys.exit(1)
        logger.info("Starting MCP → A2A bridge on %s:%d", cfg.a2a_host, cfg.a2a_port)
        asyncio.run(_run_mcp_to_a2a(cfg))

    elif direction == "a2a-to-mcp":
        if not cfg.a2a_agents:
            click.echo("Error: No a2a_agents configured. Check your config file.", err=True)
            sys.exit(1)
        logger.info("Starting A2A → MCP bridge on %s:%d", cfg.mcp_host, cfg.mcp_port)
        asyncio.run(_run_a2a_to_mcp(cfg))

    elif direction == "both":
        if not cfg.mcp_servers and not cfg.a2a_agents:
            click.echo(
                "Error: No mcp_servers or a2a_agents configured. Check your config file.",
                err=True,
            )
            sys.exit(1)
        logger.info("Starting bidirectional bridge")
        asyncio.run(_run_both(cfg))


async def _run_mcp_to_a2a(cfg: BridgeConfig) -> None:
    from mcp_a2a_bridge.mcp_to_a2a.adapter import MCPtoA2AAdapter

    adapter = MCPtoA2AAdapter(cfg)
    await adapter.run()


async def _run_a2a_to_mcp(cfg: BridgeConfig) -> None:
    from mcp_a2a_bridge.a2a_to_mcp.adapter import A2AtoMCPAdapter

    adapter = A2AtoMCPAdapter(cfg)
    await adapter.run()


async def _run_both(cfg: BridgeConfig) -> None:
    """Run both directions concurrently."""
    tasks = []

    if cfg.mcp_servers:
        from mcp_a2a_bridge.mcp_to_a2a.adapter import MCPtoA2AAdapter

        mcp_adapter = MCPtoA2AAdapter(cfg)
        tasks.append(asyncio.create_task(mcp_adapter.run()))

    if cfg.a2a_agents:
        from mcp_a2a_bridge.a2a_to_mcp.adapter import A2AtoMCPAdapter

        a2a_adapter = A2AtoMCPAdapter(cfg)
        tasks.append(asyncio.create_task(a2a_adapter.run()))

    if tasks:
        await asyncio.gather(*tasks)


# --- Quick-start commands ---


@main.command()
@click.argument("mcp_command")
@click.argument("mcp_args", nargs=-1)
@click.option("--port", "-p", default=8000, help="A2A server port.")
@click.option("--model", "-m", default="gpt-4o-mini", help="LLM model for routing.")
def quick(mcp_command: str, mcp_args: tuple[str, ...], port: int, model: str) -> None:
    """Quick-start: expose a single MCP server as an A2A agent.

    Example:
        mcp-a2a-bridge quick python -m my_mcp_server --port 8000
    """
    _setup_logging("INFO")

    cfg = BridgeConfig.from_dict(
        {
            "mcp_servers": [
                {
                    "name": mcp_command,
                    "transport": "stdio",
                    "command": mcp_command,
                    "args": list(mcp_args),
                }
            ],
            "a2a_port": port,
            "llm": {"model": model},
        }
    )

    click.echo(f"Starting MCP → A2A bridge: {mcp_command} {' '.join(mcp_args)} → :{port}")
    asyncio.run(_run_mcp_to_a2a(cfg))


@main.command()
@click.argument("agent_url")
@click.option("--port", "-p", default=9000, help="MCP server port.")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="streamable-http",
    help="MCP server transport.",
)
def expose(agent_url: str, port: int, transport: str) -> None:
    """Quick-start: expose an A2A agent as an MCP server.

    Example:
        mcp-a2a-bridge expose https://my-agent.com --port 9000
    """
    _setup_logging("INFO")

    cfg = BridgeConfig.from_dict(
        {
            "a2a_agents": [
                {
                    "name": "agent",
                    "url": agent_url,
                }
            ],
            "mcp_port": port,
            "mcp_transport": transport,
        }
    )

    click.echo(f"Starting A2A → MCP bridge: {agent_url} → :{port} ({transport})")
    asyncio.run(_run_a2a_to_mcp(cfg))


if __name__ == "__main__":
    main()
