"""Async HTTP client wrapping AnkiConnect's JSON API."""

from typing import Any

import httpx

from .config import ANKI_CONNECT_URL, ANKI_CONNECT_VERSION
from . import get_logger

logger = get_logger(__name__)


class AnkiConnectError(Exception):
    """Raised when AnkiConnect returns an error."""


class AnkiNotRunningError(AnkiConnectError):
    """Raised when Anki desktop is not running or AnkiConnect is unreachable."""

    def __init__(self):
        super().__init__(
            "Cannot reach AnkiConnect at http://127.0.0.1:8765. "
            "Make sure Anki desktop is running with the AnkiConnect addon installed "
            "(addon code 2055492159)."
        )


class AnkiClient:
    """Thin async client for AnkiConnect (localhost:8765)."""

    def __init__(self, url: str = ANKI_CONNECT_URL):
        self.url = url

    async def _invoke(self, action: str, **params: Any) -> Any:
        """Send a single request to AnkiConnect."""
        payload: dict[str, Any] = {
            "action": action,
            "version": ANKI_CONNECT_VERSION,
        }
        if params:
            payload["params"] = params

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.url, json=payload, timeout=30.0)
                resp.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise AnkiNotRunningError()

        result = resp.json()
        if result.get("error"):
            raise AnkiConnectError(result["error"])
        return result.get("result")

    async def _invoke_multi(self, actions: list[dict]) -> list[Any]:
        """Batch multiple actions via AnkiConnect's multi endpoint."""
        result = await self._invoke("multi", actions=actions)
        # multi returns list of {result, error} dicts
        results = []
        for item in result:
            if item.get("error"):
                raise AnkiConnectError(item["error"])
            results.append(item.get("result"))
        return results

    # --- Note operations ---

    async def add_notes(self, notes: list[dict]) -> list[int | None]:
        """Add multiple notes. Returns list of note IDs (None for duplicates)."""
        return await self._invoke("addNotes", notes=notes)

    async def find_notes(self, query: str) -> list[int]:
        """Find note IDs matching an Anki search query."""
        return await self._invoke("findNotes", query=query)

    async def notes_info(self, note_ids: list[int]) -> list[dict]:
        """Get detailed info for a list of note IDs."""
        return await self._invoke("notesInfo", notes=note_ids)

    async def update_note(self, note_id: int, fields: dict, tags: list[str] | None = None) -> None:
        """Update a note's fields and optionally its tags."""
        note: dict[str, Any] = {"id": note_id, "fields": fields}
        if tags is not None:
            note["tags"] = tags
        await self._invoke("updateNote", note=note)

    async def delete_notes(self, note_ids: list[int]) -> None:
        """Delete notes by their IDs."""
        await self._invoke("deleteNotes", notes=note_ids)

    # --- Deck operations ---

    async def deck_names_and_ids(self) -> dict:
        """Get all deck names mapped to their IDs."""
        return await self._invoke("deckNamesAndIds")

    async def get_deck_stats(self, decks: list[str]) -> dict:
        """Get review statistics for specified decks."""
        return await self._invoke("getDeckStats", decks=decks)

    async def create_deck(self, name: str) -> int:
        """Create a deck (supports :: hierarchy). Returns deck ID."""
        return await self._invoke("createDeck", deck=name)

    # --- Bulk helpers ---

    async def find_and_get_notes(self, query: str, limit: int = 20) -> list[dict]:
        """Find notes + get their info in a single multi round-trip."""
        note_ids = await self.find_notes(query)
        if not note_ids:
            return []
        note_ids = note_ids[:limit]
        return await self.notes_info(note_ids)

    async def get_all_deck_stats(self) -> tuple[dict, dict]:
        """Get deck names/IDs + stats in a single multi round-trip."""
        actions = [
            {"action": "deckNamesAndIds", "version": ANKI_CONNECT_VERSION},
            {"action": "deckNamesAndIds", "version": ANKI_CONNECT_VERSION},
        ]
        # First get names, then we need the names to get stats
        names_and_ids = await self.deck_names_and_ids()
        deck_names = list(names_and_ids.keys())
        if not deck_names:
            return names_and_ids, {}
        stats = await self.get_deck_stats(deck_names)
        return names_and_ids, stats

    # --- Export/Import ---

    async def export_package(self, deck: str, path: str, include_sched: bool = False) -> None:
        """Export a deck to .apkg file."""
        await self._invoke(
            "exportPackage",
            deck=deck,
            path=path,
            includeSched=include_sched,
        )

    async def import_package(self, path: str) -> None:
        """Import an .apkg file."""
        await self._invoke("importPackage", path=path)

    # --- Sync ---

    async def sync(self) -> None:
        """Trigger AnkiWeb sync."""
        await self._invoke("sync")

    # --- Diagnostics ---

    async def version(self) -> str:
        """Get AnkiConnect version."""
        return await self._invoke("version")
