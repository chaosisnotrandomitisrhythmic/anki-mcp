"""Pydantic models for Anki MCP."""

from pydantic import BaseModel, Field

from .config import DEFAULT_DECK, DEFAULT_MODEL


class NoteInput(BaseModel):
    front: str = Field(..., description="Front side of the card (question)")
    back: str = Field(..., description="Back side of the card (answer)")
    tags: list[str] = Field(default=[], description="Tags (lowercase, hyphenated)")
    deck: str = Field(default=DEFAULT_DECK, description="Target deck name")
    model: str = Field(default=DEFAULT_MODEL, description="Note type (e.g. Basic, Cloze)")


class NoteInfo(BaseModel):
    note_id: int = Field(..., description="AnkiConnect note ID")
    front: str = Field(default="", description="Front field content")
    back: str = Field(default="", description="Back field content")
    tags: list[str] = Field(default=[], description="Tags on this note")
    deck: str = Field(default="", description="Deck containing this note")
    model: str = Field(default="", description="Note type name")


class DeckStats(BaseModel):
    name: str = Field(..., description="Deck name")
    deck_id: int = Field(..., description="Deck ID")
    new_count: int = Field(default=0, description="New cards due")
    learn_count: int = Field(default=0, description="Cards in learning")
    review_count: int = Field(default=0, description="Cards due for review")
    total_in_deck: int = Field(default=0, description="Total cards in deck")
