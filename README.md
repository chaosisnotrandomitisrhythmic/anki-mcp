# anki-mcp

MCP server for [Anki](https://apps.ankiweb.net/) via [AnkiConnect](https://foosoft.net/projects/anki-connect/) — create, search, and manage flashcards directly from Claude Code or any MCP client.

## Features

- **Card CRUD** — create (bulk with duplicate detection), search, update, delete
- **Deck management** — list, create (supports `::` hierarchy)
- **Archive & sync** — export/import `.apkg` files, trigger AnkiWeb sync
- **Progress analytics** — deck maturity, Interest Heat Score (which topics you retain best), study streak
- **Daily progress script** — cron-friendly report generator that reads Anki's SQLite directly

## Prerequisites

- [Anki](https://apps.ankiweb.net/) desktop running
- [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon installed (addon code `2055492159`)

## Installation

```bash
# Clone
git clone https://github.com/chaosisnotrandomitisrhythmic/anki-mcp.git
cd anki-mcp

# Install with uv (recommended)
uv sync
```

## Usage

### Claude Code

Add to your MCP config (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "anki": {
      "command": "uv",
      "args": ["--directory", "/path/to/anki-mcp", "run", "anki-mcp"]
    }
  }
}
```

### Claude Desktop

```json
{
  "mcpServers": {
    "anki": {
      "command": "uv",
      "args": ["--directory", "/path/to/anki-mcp", "run", "anki-mcp"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `add_notes` | Create flashcards (bulk, with duplicate detection) |
| `search_notes` | Find cards using Anki query syntax |
| `update_note` | Edit a card's fields or tags |
| `delete_notes` | Remove cards by ID |
| `list_decks` | All decks with card counts (new/learn/review) |
| `create_deck` | Create a deck (supports `::` hierarchy) |
| `export_deck` | Export deck to `.apkg` (optionally archive + delete) |
| `import_deck` | Restore `.apkg` from archive |
| `sync` | Trigger AnkiWeb sync |
| `progress` | Learning report with Interest Heat Score |
| `health` | Check AnkiConnect connectivity |

## Configuration

All configuration is via environment variables with sensible defaults:

| Variable | Description | Default |
|----------|-------------|---------|
| `ANKI_MCP_ARCHIVE_DIR` | Directory for `.apkg` exports/imports | `~/.local/share/anki-mcp/archive` |
| `ANKI_DB_PATH` | Path to Anki's `collection.anki2` | Platform-aware (`~/Library/Application Support/Anki2/User 1/collection.anki2` on macOS, `~/.local/share/Anki2/User 1/collection.anki2` on Linux) |
| `ANKI_MCP_OUTPUT_DIR` | Directory for daily progress reports | `~/Anki Progress` |

## Daily Progress Script

A standalone script that reads Anki's SQLite database and generates a Markdown progress report. Works even when Anki is running (read-only via WAL mode).

```bash
# Run manually
cd /path/to/anki-mcp && uv run python scripts/daily_progress.py

# Cron example (daily at 7:03 AM)
3 7 * * * cd /path/to/anki-mcp && uv run python scripts/daily_progress.py
```

The report includes deck overview, Interest Heat Score, and study streak.

## Claude Code Skill

The `skills/SKILL.md` file provides a Claude Code skill for interactive card creation. It supports:

- `/anki` — manual card creation
- `/anki extract` — scan conversation for extractable knowledge and create cards
- `/anki progress` — show learning progress

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
