# Contributing to mcp-a2a-bridge

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/naveenkumarbaskaran/mcp-a2a-bridge.git
cd mcp-a2a-bridge
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .
ruff format .
```

## Making Changes

1. Fork the repo and create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Add or update tests for any new functionality
4. Ensure all tests pass and linting is clean
5. Open a pull request against `main`

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add streaming support for A2A responses`
- `fix: handle missing content-type in MCP discovery`
- `test: add edge case for multi-tool invocation`
- `docs: update CLI reference`

## Architecture Overview

```
MCP Client ←→ [mcp_to_a2a bridge] ←→ A2A Agent
A2A Client ←→ [a2a_to_mcp bridge] ←→ MCP Server
```

### Key Modules

- `mcp_to_a2a/` — Exposes MCP tools as an A2A agent
- `a2a_to_mcp/` — Exposes A2A agents as MCP tools
- `common/` — Shared models and utilities
- `cli.py` — Click-based CLI entry point

## Adding a New Bridge Direction

1. Create a new subpackage under `src/mcp_a2a_bridge/`
2. Implement discovery, translation, and serving layers
3. Add CLI command in `cli.py`
4. Add tests mirroring the existing pattern

## Reporting Issues

- Use GitHub Issues with a clear title and reproduction steps
- Include your Python version, config (redact secrets), and error output
- For protocol issues, include raw request/response payloads if possible

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
