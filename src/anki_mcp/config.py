"""Central config for AnkiConnect constants and MCP tool prompts."""

import os
from pathlib import Path

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
ANKI_CONNECT_VERSION = 6
ARCHIVE_DIR = Path(
    os.environ.get(
        "ANKI_MCP_ARCHIVE_DIR",
        str(Path.home() / ".local" / "share" / "anki-mcp" / "archive"),
    )
).expanduser()
DEFAULT_DECK = "Default"
DEFAULT_MODEL = "Basic"


class ToolConfig:

    SERVER_INSTRUCTIONS = (
        "Anki MCP — create and manage Anki flashcards via AnkiConnect.\n"
        "\n"
        "Prerequisites: Anki desktop must be running with AnkiConnect addon installed.\n"
        "\n"
        "Card creation tools:\n"
        "- add_notes: Create flashcards (bulk, with duplicate detection)\n"
        "- search_notes: Find existing cards using Anki query syntax\n"
        "- update_note: Edit an existing card's fields or tags\n"
        "- delete_notes: Remove cards by ID\n"
        "\n"
        "Deck management:\n"
        "- list_decks: All decks with card counts (new/learn/review)\n"
        "- create_deck: Create a new deck (supports :: hierarchy)\n"
        "\n"
        "Archive & sync:\n"
        "- export_deck: Export deck to .apkg (optionally archive + delete)\n"
        "- import_deck: Restore .apkg from archive\n"
        "- sync: Trigger AnkiWeb sync\n"
        "\n"
        "Progress & analytics:\n"
        "- progress: Learning progress report — deck maturity, Interest Heat Score "
        "(which topics consolidate fastest), study streak & consistency\n"
        "\n"
        "Diagnostics:\n"
        "- health: Check if AnkiConnect is reachable\n"
        "\n"
        "Card formatting: Use HTML in front/back fields — "
        "<code>, <b>, <kbd>, <br>, <ul><li> are all supported.\n"
        "\n"
        "When creating cards, follow atomic card principles: "
        "one concept per card, clear question on front, concise answer on back."
    )

    # add_notes
    ADD_NOTES_DESCRIPTION = (
        "Create flashcards in Anki. Handles bulk creation with duplicate detection.\n"
        "\n"
        "Args:\n"
        "    notes: List of notes, each with front, back, tags, deck, model\n"
        "\n"
        "Returns:\n"
        "    Count of added/skipped cards and any errors"
    )

    # search_notes
    SEARCH_NOTES_DESCRIPTION = (
        "Search for existing cards using Anki query syntax.\n"
        "\n"
        "Examples: 'deck:Default', 'tag:python', 'front:*terraform*',\n"
        "'added:7' (last 7 days), 'deck:AWS tag:iam'\n"
        "\n"
        "Args:\n"
        "    query: Anki search query string\n"
        "    limit: Max results to return (default 20)\n"
        "\n"
        "Returns:\n"
        "    Matching notes with their fields, tags, and IDs"
    )

    # update_note
    UPDATE_NOTE_DESCRIPTION = (
        "Edit an existing card's fields or tags.\n"
        "\n"
        "Args:\n"
        "    note_id: The note ID (from search_notes results)\n"
        "    front: New front field content (optional)\n"
        "    back: New back field content (optional)\n"
        "    tags: New tag list — replaces all existing tags (optional)\n"
        "\n"
        "Returns:\n"
        "    Confirmation of update"
    )

    # delete_notes
    DELETE_NOTES_DESCRIPTION = (
        "Delete cards by their note IDs.\n"
        "\n"
        "Args:\n"
        "    note_ids: List of note IDs to delete\n"
        "\n"
        "Returns:\n"
        "    Confirmation of deletion"
    )

    # list_decks
    LIST_DECKS_DESCRIPTION = (
        "List all Anki decks with card counts.\n"
        "\n"
        "Returns:\n"
        "    All decks with new/learn/review counts and total cards"
    )

    # create_deck
    CREATE_DECK_DESCRIPTION = (
        "Create a new deck. Supports :: for nested hierarchy (e.g. 'AWS::IAM').\n"
        "\n"
        "Args:\n"
        "    name: Deck name (use :: for sub-decks)\n"
        "\n"
        "Returns:\n"
        "    Deck ID of the created deck"
    )

    # export_deck
    EXPORT_DECK_DESCRIPTION = (
        "Export a deck to .apkg file in the configured archive directory.\n"
        "\n"
        "Args:\n"
        "    deck: Deck name to export\n"
        "    archive: If true, also delete the deck from Anki after export\n"
        "\n"
        "Returns:\n"
        "    Path to the exported .apkg file"
    )

    # import_deck
    IMPORT_DECK_DESCRIPTION = (
        "Import/restore a .apkg file from the archive directory.\n"
        "\n"
        "Args:\n"
        "    filename: Name of the .apkg file in the configured archive directory\n"
        "\n"
        "Returns:\n"
        "    Confirmation of import"
    )

    # sync
    SYNC_DESCRIPTION = (
        "Trigger AnkiWeb sync.\n"
        "\n"
        "Returns:\n"
        "    Confirmation that sync completed"
    )

    # health
    HEALTH_DESCRIPTION = (
        "Check if AnkiConnect is reachable and get Anki version.\n"
        "\n"
        "Returns:\n"
        "    Connection status and Anki version info"
    )

    # progress
    PROGRESS_DESCRIPTION = (
        "Show learning progress: deck maturity, Interest Heat Score, study consistency.\n"
        "\n"
        "Interest Heat Score ranks tags by how well knowledge consolidates — "
        "high scores reveal where genuine interest lives (effortless retention).\n"
        "\n"
        "Syncs with AnkiWeb first to include mobile reviews.\n"
        "\n"
        "Args:\n"
        "    deck: Optional deck name to scope the report (default: all decks)\n"
        "    top_n: Number of top tags to show in heat ranking (default: 15)\n"
        "\n"
        "Returns:\n"
        "    Markdown report with deck overview, interest heat, and study streak"
    )
