"""Tests for metrics module — pure functions, no I/O needed."""

import pytest

from anki_mcp.metrics import (
    _ease_stability,
    _heat_bar,
    _heat_score,
    _interval_velocity,
    _maturity_ratio,
    _retention,
    compute_deck_overview,
    compute_interest_heat,
    compute_study_consistency,
    format_progress_report,
)


# --- Component functions ---

def test_interval_velocity_zero():
    assert _interval_velocity(0.0) == 0.0


def test_interval_velocity_increases():
    assert _interval_velocity(30.0) > _interval_velocity(10.0)


def test_interval_velocity_bounded():
    assert 0.0 <= _interval_velocity(1000.0) <= 1.0


def test_ease_stability_low():
    assert _ease_stability(1300.0) == 0.0


def test_ease_stability_high():
    assert _ease_stability(3500.0) == 1.0


def test_ease_stability_mid():
    score = _ease_stability(2400.0)
    assert 0.0 < score < 1.0


def test_retention_zero_reps():
    assert _retention(0, 0) == 0.0


def test_retention_perfect():
    assert _retention(100, 0) == 1.0


def test_retention_some_lapses():
    assert _retention(100, 10) == 0.9


def test_maturity_ratio_empty():
    assert _maturity_ratio([]) == 0.0


def test_maturity_ratio_all_mature():
    assert _maturity_ratio([30, 60, 90]) == 1.0


def test_maturity_ratio_none_mature():
    assert _maturity_ratio([1, 5, 10]) == 0.0


def test_maturity_ratio_mixed():
    assert _maturity_ratio([1, 30]) == 0.5


def test_heat_score_weights():
    # 40% iv + 30% es + 20% ret + 10% mat
    assert _heat_score(1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)
    assert _heat_score(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_heat_bar_empty():
    assert _heat_bar(0.0) == "[-----]"


def test_heat_bar_full():
    assert _heat_bar(1.0) == "[#####]"


def test_heat_bar_half():
    bar = _heat_bar(0.5)
    assert len(bar) == 7  # [ + 5 chars + ]
    assert "#" in bar and "-" in bar


# --- Composite functions ---

def _make_card(interval=30, factor=2500, lapses=0, reps=10, queue=2, tags=None, deck="Test"):
    return {
        "interval": interval,
        "factor": factor,
        "lapses": lapses,
        "reps": reps,
        "queue": queue,
        "tags": tags or ["python"],
        "deck_name": deck,
    }


def test_compute_interest_heat_not_enough_cards():
    cards = [_make_card(tags=["unique-tag-1"]), _make_card(tags=["unique-tag-2"])]
    result = compute_interest_heat(cards)
    assert "Not enough tagged cards" in result


def test_compute_interest_heat_with_cards():
    cards = [_make_card(tags=["python"]) for _ in range(5)]
    result = compute_interest_heat(cards)
    assert "python" in result
    assert "Heat" in result


def test_compute_deck_overview():
    cards = [_make_card(deck="Test", interval=30)]
    stats = {"Test": {"total": 1, "new_count": 0, "learn_count": 0, "review_count": 1}}
    result = compute_deck_overview(cards, stats)
    assert "Test" in result
    assert "Deck Overview" in result


def test_compute_study_consistency_empty():
    result = compute_study_consistency({})
    assert "0 card(s) reviewed" in result
    assert "0 day(s)" in result


def test_compute_study_consistency_with_data():
    review_map = {0: 20, 1: 15, 2: 10}
    result = compute_study_consistency(review_map)
    assert "20 card(s) reviewed" in result
    assert "3 day(s)" in result


def test_format_progress_report():
    cards = [_make_card() for _ in range(5)]
    stats = {"Test": {"total": 5, "new_count": 0, "learn_count": 0, "review_count": 5}}
    review_map = {0: 10}
    report = format_progress_report(cards, stats, review_map)
    assert "Anki Progress" in report
    assert "Deck Overview" in report
    assert "Interest Heat" in report
    assert "Study Consistency" in report
