"""Generate MCP tools from A2A agent cards and skills."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def agent_card_to_mcp_tools(
    agent_card: dict[str, Any],
    agent_url: str,
) -> list[dict[str, Any]]:
    """Convert an A2A AgentCard into MCP tool definitions.

    Two strategies:
    1. If the agent has skills → one MCP tool per skill
    2. If no skills → one generic "ask_<agent>" tool

    Args:
        agent_card: The agent card dict (from /.well-known/agent-card.json).
        agent_url: The base URL of the A2A agent.

    Returns:
        List of MCP tool definition dicts with name, description, inputSchema.
    """
    agent_name = agent_card.get("name", "agent")
    safe_name = _sanitize_name(agent_name)

    skills = agent_card.get("skills", [])

    if not skills:
        # Single generic tool for the whole agent
        return [
            {
                "name": f"ask_{safe_name}",
                "description": (
                    f"Send a message to the '{agent_name}' A2A agent. "
                    f"{agent_card.get('description', '')}"
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The natural language message to send to the agent.",
                        },
                    },
                    "required": ["message"],
                },
                "_agent_url": agent_url,
                "_skill_id": None,
            }
        ]

    tools = []
    for skill in skills:
        skill_id = skill.get("id", skill.get("name", "unknown"))
        skill_name = skill.get("name", skill_id)
        skill_desc = skill.get("description", f"Skill from {agent_name}")
        tool_name = f"{safe_name}_{_sanitize_name(skill_name)}"

        tools.append(
            {
                "name": tool_name,
                "description": f"[{agent_name}] {skill_desc}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": (
                                f"Natural language query for the '{skill_name}' skill. "
                                f"Examples: {', '.join(skill.get('examples', []))}"
                            ),
                        },
                    },
                    "required": ["message"],
                },
                "_agent_url": agent_url,
                "_skill_id": skill_id,
            }
        )

    logger.info(
        "Generated %d MCP tools from A2A agent '%s'",
        len(tools),
        agent_name,
    )
    return tools


def _sanitize_name(name: str) -> str:
    """Convert a human-readable name to a valid tool/function identifier."""
    # Replace non-alphanumeric with underscores, collapse multiple, strip edges
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return sanitized or "tool"
