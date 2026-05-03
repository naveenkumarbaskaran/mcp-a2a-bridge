"""Tests for A2A → MCP bridge components."""


from mcp_a2a_bridge.a2a_to_mcp.tool_factory import (
    _sanitize_name,
    agent_card_to_mcp_tools,
)


class TestSanitizeName:
    """Tests for name sanitization."""

    def test_simple(self):
        assert _sanitize_name("hello") == "hello"

    def test_spaces(self):
        assert _sanitize_name("My Tool Name") == "my_tool_name"

    def test_special_chars(self):
        assert _sanitize_name("tool@v2.0!") == "tool_v2_0"

    def test_empty(self):
        assert _sanitize_name("") == "tool"

    def test_only_special(self):
        assert _sanitize_name("@#$%") == "tool"


class TestAgentCardToMCPTools:
    """Tests for converting A2A agent cards to MCP tools."""

    def test_no_skills_generic_tool(self):
        """Agent without skills → single generic ask tool."""
        card = {
            "name": "Simple Agent",
            "description": "Does stuff.",
        }
        tools = agent_card_to_mcp_tools(card, "http://localhost:8000")
        assert len(tools) == 1
        assert tools[0]["name"] == "ask_simple_agent"
        assert "message" in tools[0]["inputSchema"]["properties"]
        assert tools[0]["_agent_url"] == "http://localhost:8000"

    def test_with_skills(self):
        """Agent with skills → one tool per skill."""
        card = {
            "name": "Order Agent",
            "skills": [
                {
                    "id": "search_orders",
                    "name": "Search Orders",
                    "description": "Search maintenance orders by criteria",
                    "examples": ["Find overdue orders in plant 1000"],
                },
                {
                    "id": "get_order",
                    "name": "Get Order",
                    "description": "Get details of a specific order",
                    "examples": ["Show order 4001234"],
                },
            ],
        }
        tools = agent_card_to_mcp_tools(card, "http://localhost:8000")
        assert len(tools) == 2
        assert tools[0]["name"] == "order_agent_search_orders"
        assert tools[1]["name"] == "order_agent_get_order"
        assert "Search maintenance orders" in tools[0]["description"]
        assert all(t["_agent_url"] == "http://localhost:8000" for t in tools)

    def test_skill_examples_in_description(self):
        """Skill examples should appear in tool description."""
        card = {
            "name": "Agent",
            "skills": [
                {
                    "id": "s1",
                    "name": "Skill One",
                    "description": "Does things",
                    "examples": ["example query"],
                },
            ],
        }
        tools = agent_card_to_mcp_tools(card, "http://x")
        assert "example query" in tools[0]["inputSchema"]["properties"]["message"]["description"]


class TestA2AResponseExtraction:
    """Tests for extracting text from A2A responses."""

    def test_extract_from_adapter(self):
        """Verify the adapter's _extract_text method."""
        from mcp_a2a_bridge.a2a_to_mcp.adapter import A2AtoMCPAdapter
        from mcp_a2a_bridge.common.config import BridgeConfig

        adapter = A2AtoMCPAdapter(BridgeConfig())

        # Artifacts format
        response = {
            "artifacts": [
                {"parts": [{"text": "Hello from agent"}]}
            ]
        }
        assert adapter._extract_text(response) == "Hello from agent"

        # Result/status/message format
        response = {
            "result": {
                "status": {
                    "message": {
                        "parts": [{"text": "Status response"}]
                    }
                }
            }
        }
        assert adapter._extract_text(response) == "Status response"

        # Direct parts format
        response = {"parts": [{"text": "Direct"}]}
        assert adapter._extract_text(response) == "Direct"
