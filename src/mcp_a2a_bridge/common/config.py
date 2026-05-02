"""Configuration loader for bridge YAML/dict configs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""

    name: str
    transport: str = "stdio"  # stdio | sse | streamable-http
    command: str | None = None  # for stdio
    args: list[str] = field(default_factory=list)  # for stdio
    url: str | None = None  # for sse / streamable-http
    env: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class A2AAgentConfig:
    """Configuration for connecting to an A2A agent."""

    name: str
    url: str
    description: str = ""
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """LLM configuration for the MCP→A2A routing agent."""

    model: str = "gpt-4o-mini"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout: int = 25


@dataclass
class BridgeConfig:
    """Top-level bridge configuration."""

    # MCP → A2A direction
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
    a2a_agent_name: str = "MCP Bridge Agent"
    a2a_agent_description: str = "An A2A agent that bridges to MCP tools."
    a2a_host: str = "0.0.0.0"
    a2a_port: int = 8000

    # A2A → MCP direction
    a2a_agents: list[A2AAgentConfig] = field(default_factory=list)
    mcp_server_name: str = "A2A Bridge Server"
    mcp_transport: str = "streamable-http"  # stdio | sse | streamable-http
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 9000

    # Shared
    llm: LLMConfig = field(default_factory=LLMConfig)
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str | Path) -> BridgeConfig:
        """Load configuration from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        return cls.from_dict(raw or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeConfig:
        """Build config from a dictionary."""
        llm_data = data.get("llm", {})
        llm = LLMConfig(**llm_data) if llm_data else LLMConfig()

        mcp_servers = [
            MCPServerConfig(**s) for s in data.get("mcp_servers", [])
        ]
        a2a_agents = [
            A2AAgentConfig(**a) for a in data.get("a2a_agents", [])
        ]

        return cls(
            mcp_servers=mcp_servers,
            a2a_agent_name=data.get("a2a_agent_name", cls.a2a_agent_name),
            a2a_agent_description=data.get(
                "a2a_agent_description", cls.a2a_agent_description
            ),
            a2a_host=data.get("a2a_host", cls.a2a_host),
            a2a_port=data.get("a2a_port", cls.a2a_port),
            a2a_agents=a2a_agents,
            mcp_server_name=data.get("mcp_server_name", cls.mcp_server_name),
            mcp_transport=data.get("mcp_transport", cls.mcp_transport),
            mcp_host=data.get("mcp_host", cls.mcp_host),
            mcp_port=data.get("mcp_port", cls.mcp_port),
            llm=llm,
            log_level=data.get("log_level", cls.log_level),
        )
