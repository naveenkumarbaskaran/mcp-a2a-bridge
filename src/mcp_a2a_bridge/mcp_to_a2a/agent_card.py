"""Auto-generate A2A AgentCard from MCP tool metadata."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


def mcp_tools_to_skills(
    tools: list[MCPTool],
    server_name: str = "",
) -> list[dict[str, Any]]:
    """Convert MCP tools to A2A AgentSkill dicts.

    Each MCP tool becomes one A2A skill. The tool's inputSchema is stored
    in the skill tags for reference.

    Args:
        tools: List of MCP Tool objects.
        server_name: Optional server name prefix for skill IDs.

    Returns:
        List of skill dicts ready for AgentSkill protobuf construction.
    """
    skills = []
    prefix = f"{server_name}." if server_name else ""

    for tool in tools:
        # Build example from input schema if possible
        examples = []
        if tool.inputSchema and "properties" in tool.inputSchema:
            param_names = list(tool.inputSchema["properties"].keys())
            if param_names:
                examples.append(f"Use {tool.name} with {', '.join(param_names)}")

        # Extract parameter names as tags for discoverability
        tags = [tool.name]
        if tool.inputSchema and "properties" in tool.inputSchema:
            tags.extend(tool.inputSchema["properties"].keys())

        skills.append(
            {
                "id": f"{prefix}{tool.name}",
                "name": tool.name,
                "description": tool.description or f"MCP tool: {tool.name}",
                "tags": tags[:10],  # Cap at 10 tags
                "examples": examples,
                "input_modes": ["text"],
                "output_modes": ["text"],
            }
        )

    logger.info(
        "Generated %d A2A skills from MCP tools%s",
        len(skills),
        f" (server: {server_name})" if server_name else "",
    )
    return skills


def build_tool_descriptions(tools: list[MCPTool]) -> str:
    """Build a formatted tool catalog string for LLM system prompts.

    Args:
        tools: List of MCP Tool objects.

    Returns:
        Formatted string describing all available tools and their parameters.
    """
    lines = []
    for tool in tools:
        lines.append(f"## {tool.name}")
        if tool.description:
            lines.append(f"{tool.description}")

        if tool.inputSchema and "properties" in tool.inputSchema:
            lines.append("Parameters:")
            props = tool.inputSchema["properties"]
            required = set(tool.inputSchema.get("required", []))
            for pname, pschema in props.items():
                req_marker = " (required)" if pname in required else " (optional)"
                ptype = pschema.get("type", "any")
                pdesc = pschema.get("description", "")
                lines.append(f"  - {pname}: {ptype}{req_marker} — {pdesc}")

        lines.append("")

    return "\n".join(lines)
