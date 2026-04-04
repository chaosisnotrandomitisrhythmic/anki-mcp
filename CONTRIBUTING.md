# Contributing to anki-mcp

Thanks for your interest in contributing!

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Anki](https://apps.ankiweb.net/) desktop with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon

## Setup

```bash
git clone https://github.com/chaosisnotrandomitisrhythmic/anki-mcp.git
cd anki-mcp
uv sync
```

## Running locally

```bash
# Start the MCP server
uv run anki-mcp

# Run the daily progress script
uv run python scripts/daily_progress.py
```

## Project structure

```
src/anki_mcp/
  __init__.py       # Logger setup + run_server entry point
  config.py         # Constants, env var defaults, tool descriptions
  client.py         # Async AnkiConnect HTTP client
  models.py         # Pydantic models (NoteInput, NoteInfo, DeckStats, etc.)
  metrics.py        # Pure metric computation (Interest Heat Score, reports)
  server.py         # FastMCP server with tool definitions
scripts/
  daily_progress.py # Standalone cron-friendly progress report generator
skills/
  SKILL.md          # Claude Code skill for interactive card creation
```

## Making changes

1. Fork the repo and create a feature branch
2. Make your changes
3. Test locally with Anki running:
   - `uv run anki-mcp` — server starts without errors
   - Test the relevant MCP tools via Claude Code or another MCP client
4. Open a pull request

## Code style

- Follow existing patterns — the codebase is small enough to read end-to-end
- Keep `metrics.py` pure (no I/O) — it's shared between the MCP server and the cron script
- Tool descriptions live in `config.py` (ToolConfig class), not inline in `server.py`
- Use env vars for any path that might differ across machines

## Reporting issues

Open an issue on GitHub. Include:
- What you expected vs what happened
- Anki version and AnkiConnect version (`health` tool output)
- OS and Python version

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
