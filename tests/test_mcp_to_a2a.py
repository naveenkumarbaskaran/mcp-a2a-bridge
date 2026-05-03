"""Tests for MCP → A2A bridge components."""


from mcp_a2a_bridge.mcp_to_a2a.agent_card import (
    build_tool_descriptions,
    mcp_tools_to_skills,
)


class FakeTool:
    """Minimal MCP Tool-like object for testing."""

    def __init__(self, name: str, description: str | None, input_schema: dict | None = None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema
        self.outputSchema = None
        self.annotations = None


class TestMCPToolsToSkills:
    """Tests for converting MCP tools to A2A skills."""

    def test_empty_tools(self):
        skills = mcp_tools_to_skills([])
        assert skills == []

    def test_single_tool(self):
        tools = [
            FakeTool(
                name="get_weather",
                description="Get weather for a city",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "City name"},
                    },
                    "required": ["city"],
                },
            )
        ]
        skills = mcp_tools_to_skills(tools)
        assert len(skills) == 1
        assert skills[0]["id"] == "get_weather"
        assert skills[0]["name"] == "get_weather"
        assert "weather" in skills[0]["description"].lower()
        assert "city" in skills[0]["tags"]

    def test_with_server_prefix(self):
        tools = [FakeTool(name="greet", description="Greet someone")]
        skills = mcp_tools_to_skills(tools, server_name="demo")
        assert skills[0]["id"] == "demo.greet"

    def test_multiple_tools(self):
        tools = [
            FakeTool(name="tool_a", description="Tool A"),
            FakeTool(name="tool_b", description="Tool B"),
            FakeTool(name="tool_c", description="Tool C"),
        ]
        skills = mcp_tools_to_skills(tools)
        assert len(skills) == 3
        assert [s["name"] for s in skills] == ["tool_a", "tool_b", "tool_c"]

    def test_no_description_fallback(self):
        tools = [FakeTool(name="mystery", description=None)]
        skills = mcp_tools_to_skills(tools)
        assert "mystery" in skills[0]["description"]


class TestBuildToolDescriptions:
    """Tests for building LLM-readable tool catalogs."""

    def test_empty(self):
        result = build_tool_descriptions([])
        assert result == ""

    def test_with_params(self):
        tools = [
            FakeTool(
                name="search",
                description="Search for items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results"},
                    },
                    "required": ["query"],
                },
            )
        ]
        result = build_tool_descriptions(tools)
        assert "## search" in result
        assert "query" in result
        assert "(required)" in result
        assert "limit" in result
        assert "(optional)" in result
