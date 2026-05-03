"""A2A AgentExecutor that bridges to MCP tool servers."""

from __future__ import annotations

import logging

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    Part,
    Task,
    TaskState,
    TaskStatus,
)
from mcp import ClientSession
from mcp.types import Tool as MCPTool

from mcp_a2a_bridge.common.config import LLMConfig
from mcp_a2a_bridge.mcp_to_a2a.tool_router import route_to_tools

logger = logging.getLogger(__name__)


class MCPBridgeExecutor(AgentExecutor):
    """A2A executor that routes natural language requests to MCP tools.

    This executor:
    1. Receives an A2A message (natural language)
    2. Uses an LLM to decide which MCP tool(s) to call
    3. Calls the tools via the MCP ClientSession
    4. Returns results as A2A artifacts
    """

    def __init__(
        self,
        mcp_sessions: dict[str, ClientSession],
        mcp_tools: list[MCPTool],
        llm_config: LLMConfig,
    ) -> None:
        """Initialize the bridge executor.

        Args:
            mcp_sessions: Map of server_name → active MCP ClientSession.
            mcp_tools: Aggregated list of all MCP tools across servers.
            llm_config: LLM configuration for tool routing.
        """
        self._sessions = mcp_sessions
        self._tools = mcp_tools
        self._tool_to_session: dict[str, ClientSession] = {}
        self._llm_config = llm_config

    def register_tool_session(self, tool_name: str, session: ClientSession) -> None:
        """Map a tool name to its owning MCP session."""
        self._tool_to_session[tool_name] = session

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle an incoming A2A request by routing to MCP tools."""
        task_id = context.task_id
        context_id = context.context_id
        user_input = context.get_user_input()

        # Create the task
        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[context.message],
            )
        )

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )
        await updater.start_work()

        try:
            # Route user query to MCP tools via LLM
            tool_calls = await route_to_tools(
                user_query=user_input,
                tools=self._tools,
                llm_config=self._llm_config,
            )

            if not tool_calls:
                # No tools matched — respond with a helpful message
                await updater.add_artifact(
                    parts=[
                        Part(
                            text=(
                                "I couldn't find a matching tool for your request. "
                                f"I have access to these tools: "
                                f"{', '.join(t.name for t in self._tools)}. "
                                "Please try rephrasing your query."
                            )
                        )
                    ],
                    name="response",
                    last_chunk=True,
                )
                await updater.complete()
                return

            # Execute each tool call
            results: list[str] = []
            for tc in tool_calls:
                tool_name = tc["tool"]
                arguments = tc.get("arguments", {})

                session = self._tool_to_session.get(tool_name)
                if not session:
                    results.append(f"[{tool_name}] Error: No session found for this tool.")
                    continue

                logger.info("Calling MCP tool: %s(%s)", tool_name, arguments)
                try:
                    result = await session.call_tool(tool_name, arguments)

                    if result.isError:
                        results.append(f"[{tool_name}] Error: Tool returned an error.")
                        continue

                    # Collect text content from the result
                    texts = []
                    for content in result.content:
                        if hasattr(content, "text"):
                            texts.append(content.text)
                        elif hasattr(content, "data"):
                            texts.append(f"[binary data: {content.mimeType}]")

                    tool_output = "\n".join(texts) if texts else "(no output)"
                    results.append(
                        f"**{tool_name}**:\n{tool_output}"
                        if len(tool_calls) > 1
                        else tool_output
                    )

                except Exception as e:
                    logger.error("MCP tool call failed: %s — %s", tool_name, e)
                    results.append(f"[{tool_name}] Error: {e}")

            # Send combined results as artifact
            combined = "\n\n".join(results)
            await updater.add_artifact(
                parts=[Part(text=combined)],
                name="response",
                last_chunk=True,
            )
            await updater.complete()

        except Exception as e:
            logger.error("Bridge executor error: %s", e, exc_info=True)
            await updater.add_artifact(
                parts=[Part(text=f"Bridge error: {e}")],
                name="error",
                last_chunk=True,
            )
            await updater.failed()

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle task cancellation."""
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=context.task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()
