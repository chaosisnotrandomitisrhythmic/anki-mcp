# Security

## Architecture

anki-mcp communicates **only with localhost**:

- **AnkiConnect** at `http://127.0.0.1:8765` — no remote connections
- **No telemetry**, analytics, or external data collection
- **No credentials stored** — AnkiConnect requires no authentication

## Data Access

- **MCP tools**: read/write Anki data via AnkiConnect (local HTTP)
- **Daily progress script**: read-only access to Anki's SQLite database
- **Archive files**: `.apkg` exports written to a configurable local directory
- **No network access** beyond localhost AnkiConnect and AnkiWeb sync (triggered through Anki's own sync mechanism)

## Filesystem Scope

The server only writes to:
- `ANKI_MCP_ARCHIVE_DIR` (default: `~/.local/share/anki-mcp/archive/`) — `.apkg` exports
- `ANKI_MCP_OUTPUT_DIR` (default: `~/Anki Progress/`) — daily progress reports (script only)

Path traversal is guarded: `import_deck` validates that resolved paths stay inside the archive directory.

## Dependencies

- [FastMCP](https://github.com/jlowin/fastmcp) — MCP protocol server
- [httpx](https://github.com/encode/httpx) — HTTP client for AnkiConnect
- [Pydantic](https://github.com/pydantic/pydantic) — data validation

All dependencies are from well-maintained, widely-used Python packages.

## Reporting a Vulnerability

If you discover a security issue, please open a GitHub issue or email the maintainer directly. There is no bug bounty program.
