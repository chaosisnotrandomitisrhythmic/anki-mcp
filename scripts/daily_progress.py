#!/usr/bin/env python3
"""Daily Anki progress report → Markdown file.

Reads Anki's SQLite database directly (safe concurrent read via WAL mode).
Falls back gracefully if Anki is running and locks the DB.

Usage:
    cd /path/to/anki-mcp && uv run python scripts/daily_progress.py
"""

from __future__ import annotations

import json
import os
import platform
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

# Add src to path so we can import the shared metrics module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from anki_mcp.metrics import format_progress_report


def _default_anki_db() -> Path:
    """Platform-aware default path to Anki's collection database."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Anki2" / "User 1" / "collection.anki2"
    return Path.home() / ".local" / "share" / "Anki2" / "User 1" / "collection.anki2"


ANKI_DB = Path(os.environ.get("ANKI_DB_PATH", str(_default_anki_db()))).expanduser()
OUTPUT_DIR = Path(os.environ.get("ANKI_MCP_OUTPUT_DIR", str(Path.home() / "Anki Progress"))).expanduser()


def _try_ankiconnect_sync() -> bool:
    """
    Attempt to trigger an Anki sync via AnkiConnect on the local host.

    Returns:
        bool: `True` if a POST to AnkiConnect at http://127.0.0.1:8765 returned HTTP 200, `False` otherwise.
    """
    try:
        import httpx
        resp = httpx.post(
            "http://127.0.0.1:8765",
            json={"action": "sync", "version": 6},
            timeout=30.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _get_last_sync_time(db_path: Path) -> str | None:
    """
    Obtain the collection's last sync time formatted as YYYY-MM-DD HH:MM.

    Reads the `ls` value from the collection's `col` table (interpreted as milliseconds since the epoch) and converts it to a local timestamp string. Returns `None` if the value is absent or an error occurs while reading the database.

    Returns:
        str | None: A timestamp string formatted as `YYYY-MM-DD HH:MM` if available, `None` otherwise.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.execute("SELECT ls FROM col")
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            # ls is milliseconds since epoch
            ts = row[0] / 1000
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    return None


def _load_deck_names(conn: sqlite3.Connection) -> dict[int, str]:
    """Resolve deck IDs to display names.

    Newer Anki versions (>= 23.10) store decks in a separate `decks` table and
    use ASCII Unit Separator (\\x1f) instead of `::` for hierarchy. Older
    versions store the entire deck tree as JSON in `col.decks`. Try the modern
    table first; fall back to the legacy JSON column.
    """
    try:
        rows = conn.execute("SELECT id, name FROM decks").fetchall()
        if rows:
            return {int(did): name.replace("\x1f", "::") for did, name in rows}
    except sqlite3.OperationalError:
        pass  # No `decks` table — fall through to legacy JSON

    decks_json_row = conn.execute("SELECT decks FROM col").fetchone()
    if not decks_json_row or not decks_json_row[0]:
        return {}
    decks = json.loads(decks_json_row[0])
    return {int(did): d["name"] for did, d in decks.items()}


def _load_cards(db_path: Path) -> list[dict]:
    """
    Load non-suspended Anki cards from the collection SQLite and return their relevant fields.

    Parameters:
        db_path (Path): Path to the Anki collection SQLite file (opened read-only).

    Returns:
        list[dict]: A list of card records where each dictionary contains:
            - interval (int): Card interval in days (`ivl`).
            - factor (int): Ease factor (`factor`).
            - lapses (int): Number of lapses (`lapses`).
            - reps (int): Total review repetitions (`reps`).
            - queue (int): Queue/state value (`queue`).
            - tags (list[str]): Note tags as a list of strings.
            - deck_name (str): Resolved deck name for the card (or "Unknown(<did>)" if not found).
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT c.id, c.ivl, c.factor, c.lapses, c.reps, c.queue, c.did, n.tags
        FROM cards c JOIN notes n ON c.nid = n.id
        WHERE c.queue != -1
    """).fetchall()

    did_to_name = _load_deck_names(conn)
    conn.close()

    cards = []
    for r in rows:
        tags_raw = r["tags"].strip()
        tags = tags_raw.split() if tags_raw else []
        cards.append({
            "interval": r["ivl"],
            "factor": r["factor"],
            "lapses": r["lapses"],
            "reps": r["reps"],
            "queue": r["queue"],
            "tags": tags,
            "deck_name": did_to_name.get(r["did"], f"Unknown({r['did']})"),
        })

    return cards


def _load_deck_stats(db_path: Path) -> dict[str, dict]:
    """
    Aggregate per-deck card counts by queue state, excluding suspended cards.

    Parameters:
        db_path (Path): Path to the Anki collection database.

    Returns:
        dict[str, dict]: Mapping from deck name to a dictionary with the following integer keys:
            - "new_count": number of cards in the new queue (queue = 0)
            - "learn_count": number of cards in the learning queue (queue = 1)
            - "review_count": number of cards in the review queue (queue = 2)
            - "total": total number of non-suspended cards for the deck
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    did_to_name = _load_deck_names(conn)

    rows = conn.execute("""
        SELECT did,
            SUM(CASE WHEN queue = 0 THEN 1 ELSE 0 END) as new_count,
            SUM(CASE WHEN queue = 1 THEN 1 ELSE 0 END) as learn_count,
            SUM(CASE WHEN queue = 2 THEN 1 ELSE 0 END) as review_count,
            COUNT(*) as total
        FROM cards
        WHERE queue != -1
        GROUP BY did
    """).fetchall()
    conn.close()

    stats = {}
    for r in rows:
        did, new_count, learn_count, review_count, total = r
        name = did_to_name.get(did, f"Unknown({did})")
        stats[name] = {
            "new_count": new_count,
            "learn_count": learn_count,
            "review_count": review_count,
            "total": total,
        }

    return stats


def _load_review_history(db_path: Path) -> dict[int, int]:
    """
    Get daily review counts for the last 30 days from the Anki revlog.

    Parameters:
        db_path (Path): Path to the Anki collection SQLite file.

    Returns:
        dict[int, int]: Mapping where keys are days ago (0 = today) and values are the number of reviews on that day; includes only entries for days in the range 0-30.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    rows = conn.execute("""
        SELECT CAST((julianday('now', 'localtime') - julianday(id/1000, 'unixepoch', 'localtime')) AS INTEGER) as days_ago,
               COUNT(*) as cnt
        FROM revlog
        WHERE id > (strftime('%s', 'now', '-30 days') * 1000)
        GROUP BY days_ago
    """).fetchall()
    conn.close()

    return {r[0]: r[1] for r in rows if 0 <= r[0] < 31}


def main():
    """
    Generate today's Anki progress report and write it as a Markdown file.

    Attempts to sync via AnkiConnect; if unavailable, reads data directly from the configured Anki collection SQLite database. Loads card details, per-deck statistics, and recent review history, formats the report with format_progress_report, and writes the output to OUTPUT_DIR/YYYY-MM-DD.md. Exits with status code 1 if the configured ANKI_DB file does not exist.
    """
    if not ANKI_DB.exists():
        print(f"Anki database not found at {ANKI_DB}", file=sys.stderr)
        sys.exit(1)

    # Try AnkiConnect sync first (gets latest mobile reviews)
    synced = _try_ankiconnect_sync()
    if synced:
        print("Synced via AnkiConnect")
    else:
        print("AnkiConnect unavailable — using existing SQLite data")

    # Get last sync timestamp
    data_as_of = _get_last_sync_time(ANKI_DB)

    # Load data from SQLite
    cards = _load_cards(ANKI_DB)
    deck_stats = _load_deck_stats(ANKI_DB)
    review_day_map = _load_review_history(ANKI_DB)

    # Generate report
    report = format_progress_report(
        cards, deck_stats, review_day_map,
        data_as_of=data_as_of,
    )

    # Write report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    output_path = OUTPUT_DIR / f"{today}.md"
    output_path.write_text(report)

    print(f"Written to {output_path}")
    print(f"Cards: {len(cards)}, Decks: {len(deck_stats)}")


if __name__ == "__main__":
    main()
