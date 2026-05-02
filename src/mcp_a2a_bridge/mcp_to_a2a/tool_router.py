"""LLM-powered tool router: natural language → MCP tool calls."""

from __future__ import annotations

import json
import logging
from typing import Any

import litellm

from mcp.types import Tool as MCPTool

from mcp_a2a_bridge.common.config import LLMConfig
from mcp_a2a_bridge.mcp_to_a2a.agent_card import build_tool_descriptions

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
You are a tool-routing agent. Given a user query and a catalog of available tools, \
decide which tool(s) to call and with what arguments.

AVAILABLE TOOLS:
{tool_catalog}

RULES:
1. Respond ONLY with a JSON array of tool calls. No explanation, no markdown.
2. Each element: {{"tool": "<tool_name>", "arguments": {{...}}}}
3. If NO tool matches the query, respond with: []
4. Use ONLY tools listed above. Never invent tool names.
5. Infer arguments from the user query. Use null for optional params you can't infer.
6. You may call multiple tools if the query requires it.

EXAMPLES:
User: "What's the weather in Paris?"
[{{"tool": "get_weather", "arguments": {{"city": "Paris"}}}}]

User: "Hello, how are you?"
[]
"""


async def route_to_tools(
    user_query: str,
    tools: list[MCPTool],
    llm_config: LLMConfig,
) -> list[dict[str, Any]]:
    """Use an LLM to decide which MCP tools to call for a given user query.

    Args:
        user_query: The natural language query from the A2A request.
        tools: Available MCP tools.
        llm_config: LLM configuration.

    Returns:
        List of tool call dicts: [{"tool": "name", "arguments": {...}}, ...]
        Empty list if no tools match.
    """
    if not tools:
        return []

    tool_catalog = build_tool_descriptions(tools)
    system_prompt = ROUTER_SYSTEM_PROMPT.format(tool_catalog=tool_catalog)

    litellm.drop_params = True

    try:
        response = await litellm.acompletion(
            model=llm_config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            timeout=llm_config.timeout,
            api_key=llm_config.api_key,
            api_base=llm_config.api_base,
        )

        content = response.choices[0].message.content.strip()  # type: ignore[union-attr]

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        tool_calls = json.loads(content)

        if not isinstance(tool_calls, list):
            logger.warning("LLM returned non-list: %s", type(tool_calls))
            return []

        # Validate tool names
        valid_names = {t.name for t in tools}
        validated = []
        for tc in tool_calls:
            if isinstance(tc, dict) and tc.get("tool") in valid_names:
                validated.append(tc)
            else:
                logger.warning("Dropping invalid tool call: %s", tc)

        logger.info("Routed query to %d tool(s): %s", len(validated), [t["tool"] for t in validated])
        return validated

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM tool routing response: %s", e)
        return []
    except Exception as e:
        logger.error("LLM routing failed: %s", e)
        return []
