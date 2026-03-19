"""FastMCP server with Anki tools."""

import asyncio
from datetime import date, timedelta
from typing import Optional

from fastmcp import FastMCP

from .client import AnkiClient, AnkiConnectError, AnkiNotRunningError
from .config import ARCHIVE_DIR, DEFAULT_DECK, DEFAULT_MODEL, ToolConfig
from .metrics import format_progress_report
from .models import DeckStats, NoteInfo, NoteInput
from . import get_logger

logger = get_logger(__name__)

mcp = FastMCP(
    name="anki",
    instructions=ToolConfig.SERVER_INSTRUCTIONS,
)

_client = AnkiClient()


def _build_anki_note(note: NoteInput) -> dict:
    """Convert a NoteInput to AnkiConnect's addNote format."""
    return {
        "deckName": note.deck,
        "modelName": note.model,
        "fields": {"Front": note.front, "Back": note.back},
        "tags": note.tags,
        "options": {
            "allowDuplicate": False,
            "duplicateScope": "deck",
            "duplicateScopeOptions": {
                "deckName": note.deck,
                "checkChildren": True,
                "checkAllModels": False,
            },
        },
    }


def _parse_note_info(raw: dict) -> NoteInfo:
    """Parse AnkiConnect notesInfo response into a NoteInfo."""
    fields = raw.get("fields", {})
    # Front/Back are the standard field names for Basic model
    front = fields.get("Front", {}).get("value", "")
    back = fields.get("Back", {}).get("value", "")
    # For Cloze or other models, try Text/Extra
    if not front and "Text" in fields:
        front = fields["Text"].get("value", "")
    if not back and "Extra" in fields:
        back = fields["Extra"].get("value", "")

    return NoteInfo(
        note_id=raw["noteId"],
        front=front,
        back=back,
        tags=raw.get("tags", []),
        deck=raw.get("deckName", ""),
        model=raw.get("modelName", ""),
    )


@mcp.tool(description=ToolConfig.ADD_NOTES_DESCRIPTION)
async def add_notes(notes: list[NoteInput]) -> str:
    """Create flashcards in Anki."""
    anki_notes = [_build_anki_note(n) for n in notes]
    try:
        results = await _client.add_notes(anki_notes)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error adding notes: {e}"

    added = sum(1 for r in results if r is not None)
    skipped = len(results) - added

    parts = [f"Added {added} card(s) to Anki."]
    if skipped:
        parts.append(f"Skipped {skipped} duplicate(s).")

    # List which decks received cards
    decks_used = sorted(set(n.deck for n, r in zip(notes, results) if r is not None))
    if decks_used:
        parts.append(f"Decks: {', '.join(decks_used)}")

    return " ".join(parts)


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.SEARCH_NOTES_DESCRIPTION)
async def search_notes(query: str, limit: int = 20) -> str:
    """Search for cards using Anki query syntax."""
    try:
        raw_notes = await _client.find_and_get_notes(query, limit=limit)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error searching notes: {e}"

    if not raw_notes:
        return f"No notes found for query: {query}"

    parsed = [_parse_note_info(n) for n in raw_notes]
    lines = [f"Found {len(parsed)} note(s):\n"]
    for n in parsed:
        tags_str = ", ".join(n.tags) if n.tags else "(none)"
        lines.append(
            f"- **ID {n.note_id}** [{n.deck}] ({n.model})\n"
            f"  Front: {n.front[:200]}\n"
            f"  Back: {n.back[:200]}\n"
            f"  Tags: {tags_str}"
        )
    return "\n".join(lines)


@mcp.tool(description=ToolConfig.UPDATE_NOTE_DESCRIPTION)
async def update_note(
    note_id: int,
    front: Optional[str] = None,
    back: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> str:
    """Edit an existing card."""
    fields = {}
    if front is not None:
        fields["Front"] = front
    if back is not None:
        fields["Back"] = back

    if not fields and tags is None:
        return "Nothing to update — provide at least one of: front, back, tags."

    try:
        await _client.update_note(note_id, fields=fields, tags=tags)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error updating note {note_id}: {e}"

    parts = []
    if fields:
        parts.append(f"fields ({', '.join(fields.keys())})")
    if tags is not None:
        parts.append(f"tags ({len(tags)})")
    return f"Updated note {note_id}: {', '.join(parts)}."


@mcp.tool(description=ToolConfig.DELETE_NOTES_DESCRIPTION)
async def delete_notes(note_ids: list[int]) -> str:
    """Delete cards by ID."""
    try:
        await _client.delete_notes(note_ids)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error deleting notes: {e}"

    return f"Deleted {len(note_ids)} note(s)."


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.LIST_DECKS_DESCRIPTION)
async def list_decks() -> str:
    """List all decks with card counts."""
    try:
        names_and_ids, stats = await _client.get_all_deck_stats()
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error listing decks: {e}"

    if not names_and_ids:
        return "No decks found."

    decks = []
    for name, deck_id in sorted(names_and_ids.items()):
        deck_stat = stats.get(str(deck_id), {})
        decks.append(DeckStats(
            name=name,
            deck_id=deck_id,
            new_count=deck_stat.get("new_count", 0),
            learn_count=deck_stat.get("learn_count", 0),
            review_count=deck_stat.get("review_count", 0),
            total_in_deck=deck_stat.get("total_in_deck", 0),
        ))

    lines = [f"Found {len(decks)} deck(s):\n"]
    for d in decks:
        lines.append(
            f"- **{d.name}** (ID: {d.deck_id}) — "
            f"{d.total_in_deck} total, "
            f"{d.new_count} new, {d.learn_count} learning, {d.review_count} review"
        )
    return "\n".join(lines)


@mcp.tool(description=ToolConfig.CREATE_DECK_DESCRIPTION)
async def create_deck(name: str) -> str:
    """Create a new deck."""
    try:
        deck_id = await _client.create_deck(name)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error creating deck: {e}"

    return f"Created deck '{name}' (ID: {deck_id})."


@mcp.tool(description=ToolConfig.EXPORT_DECK_DESCRIPTION)
async def export_deck(deck: str, archive: bool = False) -> str:
    """Export a deck to .apkg file."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitize deck name for filename
    safe_name = deck.replace("::", "_").replace(" ", "_").replace("/", "_")
    path = str(ARCHIVE_DIR / f"{safe_name}.apkg")

    try:
        await _client.export_package(deck, path, include_sched=False)
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error exporting deck '{deck}': {e}"

    result = f"Exported '{deck}' to {path}"

    if archive:
        try:
            # Find all notes in this deck and delete them
            note_ids = await _client.find_notes(f'"deck:{deck}"')
            if note_ids:
                await _client.delete_notes(note_ids)
            result += f"\nArchived: deleted {len(note_ids)} note(s) from Anki."
        except AnkiConnectError as e:
            result += f"\nExport succeeded but failed to delete deck: {e}"

    return result


@mcp.tool(description=ToolConfig.IMPORT_DECK_DESCRIPTION)
async def import_deck(filename: str) -> str:
    """Import/restore an .apkg from archive."""
    path = ARCHIVE_DIR / filename
    if not path.exists():
        # List available files
        available = [f.name for f in ARCHIVE_DIR.glob("*.apkg")] if ARCHIVE_DIR.exists() else []
        if available:
            return f"File '{filename}' not found. Available: {', '.join(sorted(available))}"
        return f"File '{filename}' not found and archive directory is empty."

    try:
        await _client.import_package(str(path))
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error importing '{filename}': {e}"

    return f"Imported '{filename}' into Anki."


@mcp.tool(description=ToolConfig.SYNC_DESCRIPTION)
async def sync() -> str:
    """
    Trigger a synchronization with AnkiWeb.
    
    Returns:
        A status message: "AnkiWeb sync completed." on success, the string representation of an `AnkiNotRunningError` if Anki is not running, or "Error syncing: {e}" for `AnkiConnectError` cases.
    """
    try:
        await _client.sync()
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error syncing: {e}"

    return "AnkiWeb sync completed."


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.PROGRESS_DESCRIPTION)
async def progress(deck: Optional[str] = None, top_n: int = 15) -> str:
    """
    Generate a learning progress report for the specified deck or for all decks.

    Performs a best-effort sync, aggregates deck statistics, card scheduling data, and recent review counts (last 31 days), excludes suspended cards, and computes an interest/priority-based ranking to produce a formatted progress summary.

    Parameters:
        deck (Optional[str]): Deck name to limit the report to; when provided, includes that deck and its subdecks (prefix "{deck}::"). If omitted, the report covers all decks.
        top_n (int): Number of top-ranked cards to include in the report.

    Returns:
        str: A multiline, human-readable progress report that includes per-deck statistics, a top-N list of prioritized cards (Interest Heat Score), and a 31-day review-count histogram.
    """
    try:
        # Sync first to get latest mobile reviews
        try:
            await _client.sync()
        except AnkiConnectError:
            pass  # non-fatal — proceed with whatever data we have

        # Build query
        query = f'"deck:{deck}"' if deck else "deck:*"

        # Parallel: deck stats, find cards, review history
        names_and_ids_task = _client.deck_names_and_ids()
        find_cards_task = _client.find_cards(query)
        review_by_day_task = _client.num_cards_reviewed_by_day()

        names_and_ids, card_ids, review_raw = await asyncio.gather(
            names_and_ids_task, find_cards_task, review_by_day_task
        )

        # Get deck stats
        deck_names = list(names_and_ids.keys())
        if deck:
            deck_names = [n for n in deck_names if n == deck or n.startswith(f"{deck}::")]
        stats_raw = await _client.get_deck_stats(deck_names) if deck_names else {}

        # Sequential: get card details (depends on find_cards result)
        cards_raw = await _client.cards_info(card_ids) if card_ids else []

        # cardsInfo doesn't include tags — fetch from notesInfo
        note_ids = list({c["note"] for c in cards_raw if isinstance(c.get("note"), int)})
        notes_raw = await _client.notes_info(note_ids) if note_ids else []
        note_tags = {n["noteId"]: n.get("tags", []) for n in notes_raw}

        # Build deck_stats dict keyed by name
        id_to_name = {v: k for k, v in names_and_ids.items()}
        deck_stats: dict[str, dict] = {}
        for did_str, ds in stats_raw.items():
            dname = id_to_name.get(int(did_str), did_str)
            if deck and dname != deck and not dname.startswith(f"{deck}::"):
                continue
            deck_stats[dname] = {
                "new_count": ds.get("new_count", 0),
                "learn_count": ds.get("learn_count", 0),
                "review_count": ds.get("review_count", 0),
                "total": ds.get("total_in_deck", 0),
            }

        # Normalize cards to shared format (exclude suspended)
        cards = []
        for c in cards_raw:
            if c.get("queue", 0) == -1:
                continue
            tags = note_tags.get(c.get("note", 0), [])
            cards.append({
                "interval": c.get("interval", 0),
                "factor": c.get("factor", 0),
                "lapses": c.get("lapses", 0),
                "reps": c.get("reps", 0),
                "queue": c.get("queue", 0),
                "tags": tags,
                "deck_name": c.get("deckName", ""),
            })

        # Normalize review history to {days_ago: count}
        today = date.today()
        review_day_map: dict[int, int] = {}
        for entry in review_raw:
            # AnkiConnect returns [date_str, count]
            review_date_str, count = entry[0], entry[1]
            try:
                rd = date.fromisoformat(review_date_str)
                days_ago = (today - rd).days
                if 0 <= days_ago < 31:
                    review_day_map[days_ago] = count
            except (ValueError, TypeError):
                continue

        return format_progress_report(cards, deck_stats, review_day_map, top_n=top_n)

    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"Error generating progress report: {e}"


@mcp.tool(annotations={"readOnlyHint": True}, description=ToolConfig.HEALTH_DESCRIPTION)
async def health() -> str:
    """
    Check whether AnkiConnect is reachable and report its version.
    
    Returns:
        A message string: `AnkiConnect is reachable. Version: {version}` on success; the stringified `AnkiNotRunningError` message if Anki is not running; or `AnkiConnect error: {e}` for other connection errors.
    """
    try:
        version = await _client.version()
    except AnkiNotRunningError as e:
        return str(e)
    except AnkiConnectError as e:
        return f"AnkiConnect error: {e}"

    return f"AnkiConnect is reachable. Version: {version}"
