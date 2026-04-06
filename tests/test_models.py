"""Tests for Pydantic models."""

from anki_mcp.models import DeckStats, NoteInfo, NoteInput


def test_note_input_defaults():
    note = NoteInput(front="Q", back="A")
    assert note.deck == "Default"
    assert note.model == "Basic"
    assert note.tags == []


def test_note_input_custom():
    note = NoteInput(front="Q", back="A", tags=["python"], deck="CS", model="Cloze")
    assert note.deck == "CS"
    assert note.model == "Cloze"
    assert note.tags == ["python"]


def test_note_info():
    info = NoteInfo(note_id=123, front="Q", back="A", tags=["test"], deck="D", model="Basic")
    assert info.note_id == 123


def test_deck_stats():
    stats = DeckStats(name="Test", deck_id=1, new_count=5, review_count=10, total_in_deck=20)
    assert stats.learn_count == 0  # default
    assert stats.total_in_deck == 20
