"""Tests for configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_a2a_bridge.common.config import (
    A2AAgentConfig,
    BridgeConfig,
    LLMConfig,
    MCPServerConfig,
)


class TestBridgeConfig:
    """Tests for BridgeConfig parsing."""

    def test_from_dict_defaults(self):
        """Empty dict should produce valid config with defaults."""
        cfg = BridgeConfig.from_dict({})
        assert cfg.a2a_port == 8000
        assert cfg.mcp_port == 9000
        assert cfg.llm.model == "gpt-4o-mini"
        assert cfg.mcp_servers == []
        assert cfg.a2a_agents == []

    def test_from_dict_full(self):
        """Full config dict should parse all fields."""
        data = {
            "mcp_servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": "python",
                    "args": ["-m", "test"],
                }
            ],
            "a2a_agents": [
                {
                    "name": "test-agent",
                    "url": "http://localhost:9999",
                    "description": "Test agent",
                }
            ],
            "a2a_port": 3000,
            "mcp_port": 4000,
            "llm": {
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.5,
            },
            "log_level": "DEBUG",
        }
        cfg = BridgeConfig.from_dict(data)
        assert len(cfg.mcp_servers) == 1
        assert cfg.mcp_servers[0].name == "test-server"
        assert cfg.mcp_servers[0].command == "python"
        assert len(cfg.a2a_agents) == 1
        assert cfg.a2a_agents[0].url == "http://localhost:9999"
        assert cfg.a2a_port == 3000
        assert cfg.mcp_port == 4000
        assert cfg.llm.model == "claude-sonnet-4-20250514"
        assert cfg.llm.temperature == 0.5
        assert cfg.log_level == "DEBUG"

    def test_from_yaml(self, tmp_path):
        """YAML file should be parsed correctly."""
        data = {
            "mcp_servers": [{"name": "s1", "transport": "stdio", "command": "echo"}],
            "a2a_port": 5000,
        }
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(yaml.dump(data))

        cfg = BridgeConfig.from_yaml(yaml_path)
        assert cfg.a2a_port == 5000
        assert len(cfg.mcp_servers) == 1

    def test_from_yaml_not_found(self):
        """Missing YAML file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            BridgeConfig.from_yaml("/nonexistent/config.yaml")


class TestMCPServerConfig:
    """Tests for MCP server config."""

    def test_defaults(self):
        cfg = MCPServerConfig(name="test")
        assert cfg.transport == "stdio"
        assert cfg.command is None
        assert cfg.args == []

    def test_full(self):
        cfg = MCPServerConfig(
            name="server",
            transport="streamable-http",
            url="http://localhost:3000/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert cfg.transport == "streamable-http"
        assert cfg.url == "http://localhost:3000/mcp"


class TestLLMConfig:
    """Tests for LLM config."""

    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.0
        assert cfg.timeout == 25
