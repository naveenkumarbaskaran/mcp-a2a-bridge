#!/usr/bin/env python3
"""Simulated mcp-a2a-bridge demo for terminal recording."""
import time, sys, os

os.environ["TERM"] = "xterm-256color"

def c(code, text):
    return f"\033[{code}m{text}\033[0m"

def slow(text, delay=0.012):
    for ch in text:
        sys.stdout.write(ch); sys.stdout.flush(); time.sleep(delay)
    print()

def section(text):
    print(c("1;36", f"\n  {text}"))
    print(c("36", f"  {'─'*56}"))

print(c("1;33", """
  ███╗   ███╗ ██████╗██████╗     ↔     █████╗ ██████╗  █████╗
  ████╗ ████║██╔════╝██╔══██╗         ██╔══██╗╚════██╗██╔══██╗
  ██╔████╔██║██║     ██████╔╝  ████╗  ███████║ █████╔╝███████║
  ██║╚██╔╝██║██║     ██╔═══╝   ╚═══╝  ██╔══██║██╔═══╝ ██╔══██║
  ██║ ╚═╝ ██║╚██████╗██║              ██║  ██║███████╗██║  ██║
  ╚═╝     ╚═╝ ╚═════╝╚═╝              ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                    BRIDGE"""))

time.sleep(0.2)
print(c("2", "  v0.1.0 • Bidirectional MCP ↔ A2A protocol bridge"))
time.sleep(0.4)

# Step 1: MCP → A2A
section("$ mcp-a2a-bridge quick python -m my_mcp_server")
time.sleep(0.3)

print(c("2", "  Discovering MCP server capabilities..."))
time.sleep(0.4)

tools = [
    ("greet",        "Greet someone by name",              "str → str"),
    ("current_time", "Get current date and time",          "() → str"),
    ("calculate",    "Evaluate math expression safely",    "str → str"),
]
print(f"\n  {c('1','MCP Tools Discovered:')}")
for name, desc, sig in tools:
    print(f"    {c('32','✓')} {c('1',name):20s} {c('2',desc):38s} {c('36',sig)}")
    time.sleep(0.12)

time.sleep(0.3)
print(c("33", "\n  Generating A2A AgentCard..."))
time.sleep(0.4)

card = {
    "name": "my_mcp_server",
    "description": "Auto-bridged from MCP server (3 tools)",
    "skills": ["greet", "current_time", "calculate"],
    "endpoint": "http://localhost:8000",
}
print(c("2", "  {"))
print(f'    {c("36",chr(34)+"name"+chr(34))}: {c("32",chr(34)+card["name"]+chr(34))},')
print(f'    {c("36",chr(34)+"skills"+chr(34))}: {c("32","["+chr(34)+"greet"+chr(34)+", "+chr(34)+"current_time"+chr(34)+", "+chr(34)+"calculate"+chr(34)+"]")},')
print(f'    {c("36",chr(34)+"endpoint"+chr(34))}: {c("32",chr(34)+card["endpoint"]+chr(34))}')
print(c("2", "  }"))

time.sleep(0.3)
print(f"\n  {c('1;32','✓')} A2A agent running at {c('1','http://localhost:8000')}")
print(f"    {c('2','AgentCard')}: http://localhost:8000/.well-known/agent-card.json")

# Step 2: Calling via A2A
section("$ curl -X POST http://localhost:8000/a2a -d '...'")
time.sleep(0.3)

print(c("2", "  Incoming A2A request → translating to MCP tool call..."))
time.sleep(0.3)

print(f"\n  {c('33','A2A Request')} ──→ {c('36','MCP Call')} ──→ {c('32','Response')}")
time.sleep(0.2)
print(f"    {c('33','task: calculate(\"42 * 17\")')}")
print(f"    {c('36','→ mcp.call_tool(\"calculate\", expression=\"42 * 17\")')}")
time.sleep(0.4)
print(f"    {c('32','← \"42 * 17 = 714\"')}")
time.sleep(0.3)

# Step 3: A2A → MCP direction
section("Reverse: A2A → MCP")
time.sleep(0.2)

print(c("2", "  Exposing remote A2A agent as local MCP tool server..."))
time.sleep(0.3)

print(f"\n  {c('33','▸')} Connecting to A2A agent at https://agent.example.com")
time.sleep(0.3)
print(f"  {c('32','✓')} Agent skills mapped to MCP tools:")

skills = [
    ("summarize_text",   "Summarize documents with AI"),
    ("translate",        "Translate text between languages"),
    ("analyze_sentiment","Detect sentiment in text"),
]
for name, desc in skills:
    print(f"    {c('32','✓')} {c('1',name):24s} {c('2',desc)}")
    time.sleep(0.1)

print(f"\n  {c('1;32','✓')} MCP server running — use in Claude Desktop, Cursor, etc.")

# Summary
time.sleep(0.4)
print(c("1;36", f"\n  {'─'*56}"))
print(c("1;33", "  ┌──────────────┐         ┌──────────────┐"))
print(c("1;33", "  │  MCP Server  │ ◄─────► │  A2A Agent   │"))
print(c("1;33", "  └──────────────┘  bridge  └──────────────┘"))
print(c("1;32", "\n  ✓ Bidirectional • Auto AgentCard • Zero config"))
print(c("2",    "    pip install mcp-a2a-bridge"))
print(c("1;36", f"  {'─'*56}\n"))
time.sleep(1.0)
