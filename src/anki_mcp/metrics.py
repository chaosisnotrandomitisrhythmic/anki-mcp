"""Pure metric computation — shared by MCP tool and cron script.

All functions take normalized data (plain dicts/lists) and return markdown strings.
No I/O, no AnkiConnect, no SQLite — just math and formatting.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date


# ---------- Types (just dicts) ----------
# Card dict: {"interval": int, "factor": int, "lapses": int, "reps": int,
#              "queue": int, "tags": list[str], "deck_name": str}
# Deck stat dict: {"new_count": int, "learn_count": int, "review_count": int, "total": int}
# Review-day map: {days_ago: review_count, ...}


# ---------- Interest Heat Score ----------

_MIN_CARDS = 3  # tags with fewer cards are excluded (noise)
_MATURE_THRESHOLD = 21  # days — Anki's standard threshold


def _interval_velocity(avg_interval: float) -> float:
    """
    Convert an average interval in days to a bounded velocity score that increases toward 1.0.

    Parameters:
        avg_interval (float): Average interval in days.

    Returns:
        score (float): A value between 0.0 and 1.0; larger intervals produce higher scores and the value approaches 1.0 asymptotically with a characteristic scale of about 90 days.
    """
    return 1.0 - math.exp(-avg_interval / 90.0)


def _ease_stability(avg_factor: float) -> float:
    """
    Map an average Anki factor to a stability score in the range 0.0-1.0.

    Parameters:
        avg_factor (float): Average Anki factor (typical observed range 1300-3500).

    Returns:
        float: Stability score between 0.0 and 1.0; values below 1300 yield 0.0, values above 3500 yield 1.0.
    """
    return max(0.0, min(1.0, (avg_factor - 1300) / (3500 - 1300)))


def _retention(total_reps: int, total_lapses: int) -> float:
    """
    Compute the retention fraction from total repetitions and lapses.

    Parameters:
        total_reps (int): Total number of review repetitions.
        total_lapses (int): Total number of lapses (failed reviews).

    Returns:
        float: The retention ratio (total_reps - total_lapses) / total_reps. Returns 0.0 when `total_reps` is 0.
    """
    if total_reps == 0:
        return 0.0
    return (total_reps - total_lapses) / total_reps


def _maturity_ratio(intervals: list[int]) -> float:
    """
    Compute the fraction of intervals that meet or exceed the maturity threshold.

    Parameters:
        intervals (list[int]): Review intervals in days.

    Returns:
        float: Fraction between 0.0 and 1.0 representing the proportion of `intervals` that are greater than or equal to `_MATURE_THRESHOLD`. Returns 0.0 if `intervals` is empty.
    """
    if not intervals:
        return 0.0
    return sum(1 for i in intervals if i >= _MATURE_THRESHOLD) / len(intervals)


def _heat_score(
    iv: float, es: float, ret: float, mat: float
) -> float:
    """
    Compute a weighted composite heat score from component metrics.

    Parameters:
        iv (float): Interval velocity component in range [0.0, 1.0].
        es (float): Ease stability component in range [0.0, 1.0].
        ret (float): Retention component in range [0.0, 1.0].
        mat (float): Maturity ratio component in range [0.0, 1.0].

    Returns:
        float: Composite score in range [0.0, 1.0] computed as 40% interval velocity, 30% ease stability, 20% retention, and 10% maturity.
    """
    return 0.4 * iv + 0.3 * es + 0.2 * ret + 0.1 * mat


def _heat_bar(score: float, width: int = 5) -> str:
    """
    Render a fixed-width heat bar representing a normalized score.

    Parameters:
        score (float): Normalized score where 0.0 maps to no filled segments and 1.0 maps to all segments filled.
        width (int): Total number of segments in the bar (default 5).

    Returns:
        A fixed-width bar string enclosed in brackets where `#` denotes filled segments and `-` denotes unfilled segments (e.g., `[##---]`).
    """
    filled = round(score * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def compute_interest_heat(cards: list[dict], top_n: int = 15) -> str:
    """
    Rank tags by a composite "Interest Heat" score and render the top tags as a Markdown table.

    Generates a markdown section containing the top `top_n` tags sorted by a weighted heat score derived from card intervals, ease/factor, retention, and maturity. Tags with fewer than 3 associated cards are omitted. If no tag meets the minimum card requirement, returns a short message explaining that.

    Cards with queue == -1 (suspended) should already be filtered out upstream.

    Parameters:
        cards (list[dict]): Normalized card records; each card is expected to contain keys such as `"tags"`, `"interval"`, `"factor"`, `"reps"`, and `"lapses"`. Suspended cards (e.g., `queue == -1`) should be filtered out by the caller.
        top_n (int): Maximum number of tag rows to include in the output (default 15).

    Returns:
        str: A markdown-formatted string for the "Interest Heat" section. When tags are available, this is a table with columns for tag, card count, heat percentage (with a visual bar), and component percentages; otherwise a short explanatory message.
    """
    # Group cards by tag
    tag_cards: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        for tag in card.get("tags", []):
            tag_cards[tag].append(card)

    rows: list[tuple[float, str, int, float, float, float, float]] = []
    for tag, tcards in tag_cards.items():
        if len(tcards) < _MIN_CARDS:
            continue

        intervals = [c["interval"] for c in tcards]
        factors = [c["factor"] for c in tcards if c["factor"] > 0]
        total_reps = sum(c["reps"] for c in tcards)
        total_lapses = sum(c["lapses"] for c in tcards)

        avg_interval = sum(intervals) / len(intervals) if intervals else 0.0
        avg_factor = sum(factors) / len(factors) if factors else 2500.0

        iv = _interval_velocity(avg_interval)
        es = _ease_stability(avg_factor)
        ret = _retention(total_reps, total_lapses)
        mat = _maturity_ratio(intervals)
        score = _heat_score(iv, es, ret, mat)

        rows.append((score, tag, len(tcards), iv, es, ret, mat))

    rows.sort(key=lambda r: r[0], reverse=True)
    rows = rows[:top_n]

    if not rows:
        return "## Interest Heat\n\nNot enough tagged cards (need ≥3 per tag).\n"

    lines = [
        "## Interest Heat\n",
        "| Tag | Cards | Heat | Velocity | Ease | Retention | Mature |",
        "|-----|-------|------|----------|------|-----------|--------|",
    ]
    for score, tag, count, iv, es, ret, mat in rows:
        bar = _heat_bar(score)
        lines.append(
            f"| {tag} | {count} | {bar} {score:.0%} | {iv:.0%} | {es:.0%} | {ret:.0%} | {mat:.0%} |"
        )
    lines.append("")
    return "\n".join(lines)


# ---------- Deck Overview ----------

def compute_deck_overview(cards: list[dict], deck_stats: dict[str, dict]) -> str:
    """
    Render a markdown "Deck Overview" table summarizing counts and maturity per deck.

    Parameters:
        cards (list[dict]): Card records; each must include at least the keys
            "deck_name" and "interval".
        deck_stats (dict[str, dict]): Mapping from deck name to counts. Each deck
            dict is expected to provide the keys "total", "new_count", "learn_count",
            and "review_count".

    Notes:
        Maturity buckets are computed from card intervals using the module-level
        threshold `_MATURE_THRESHOLD`: a card is "mature" when its interval is
        greater than or equal to `_MATURE_THRESHOLD`, "young" when its interval is
        greater than 0 and less than `_MATURE_THRESHOLD`.

    Returns:
        str: Markdown-formatted table with columns: Deck, Total, New, Learning, Young,
        Mature, Due Today, and a final "All" summary row.
    """
    # Compute maturity from cards themselves
    deck_maturity: dict[str, dict] = defaultdict(lambda: {"young": 0, "mature": 0})
    for card in cards:
        dn = card["deck_name"]
        if card["interval"] >= _MATURE_THRESHOLD:
            deck_maturity[dn]["mature"] += 1
        elif card["interval"] > 0:
            deck_maturity[dn]["young"] += 1

    lines = [
        "## Deck Overview\n",
        "| Deck | Total | New | Learning | Young | Mature | Due Today |",
        "|------|-------|-----|----------|-------|--------|-----------|",
    ]

    totals = {"total": 0, "new": 0, "learn": 0, "young": 0, "mature": 0, "due": 0}

    for deck_name in sorted(deck_stats.keys()):
        ds = deck_stats[deck_name]
        mat = deck_maturity.get(deck_name, {"young": 0, "mature": 0})
        due = ds.get("new_count", 0) + ds.get("learn_count", 0) + ds.get("review_count", 0)

        total = ds.get("total", 0)
        new = ds.get("new_count", 0)
        learn = ds.get("learn_count", 0)
        young = mat["young"]
        mature = mat["mature"]

        totals["total"] += total
        totals["new"] += new
        totals["learn"] += learn
        totals["young"] += young
        totals["mature"] += mature
        totals["due"] += due

        lines.append(f"| {deck_name} | {total} | {new} | {learn} | {young} | {mature} | {due} |")

    lines.append(
        f"| **All** | **{totals['total']}** | **{totals['new']}** | **{totals['learn']}** "
        f"| **{totals['young']}** | **{totals['mature']}** | **{totals['due']}** |"
    )
    lines.append("")
    return "\n".join(lines)


# ---------- Study Consistency ----------

def compute_study_consistency(review_day_map: dict[int, int]) -> str:
    """
    Format study-consistency metrics from a mapping of days-ago to review counts into a Markdown section.

    Parameters:
        review_day_map (dict[int, int]): Mapping where keys are days ago (0 = today) and values are review counts.

    Returns:
        str: A Markdown-formatted "Study Consistency" section that includes today's review count, the current consecutive-review streak starting at day 0, the 7-day and 30-day average reviews per day, and the total reviews over the last 30 days.
    """
    today_count = review_day_map.get(0, 0)

    # Current streak: consecutive days with reviews, starting from today
    streak = 0
    for d in range(0, 31):
        if review_day_map.get(d, 0) > 0:
            streak += 1
        else:
            break

    # Averages
    days_7 = [review_day_map.get(d, 0) for d in range(7)]
    days_30 = [review_day_map.get(d, 0) for d in range(30)]
    avg_7 = sum(days_7) / 7 if days_7 else 0.0
    avg_30 = sum(days_30) / 30 if days_30 else 0.0
    total_30 = sum(days_30)

    lines = [
        "## Study Consistency\n",
        f"- **Today**: {today_count} card(s) reviewed",
        f"- **Current streak**: {streak} day(s)",
        f"- **Avg cards/day (7d)**: {avg_7:.1f}",
        f"- **Avg cards/day (30d)**: {avg_30:.1f}",
        f"- **Total reviews (30d)**: {total_30}",
        "",
    ]
    return "\n".join(lines)


# ---------- Full Report ----------

def format_progress_report(
    cards: list[dict],
    deck_stats: dict[str, dict],
    review_day_map: dict[int, int],
    top_n: int = 15,
    data_as_of: str | None = None,
) -> str:
    """
    Builds the complete Markdown progress report by assembling a dated header and the deck overview, interest heat, and study consistency sections.

    Returns:
        The full report as a Markdown-formatted string.
    """
    today = date.today().isoformat()
    header = f"# Anki Progress — {today}\n"
    if data_as_of:
        header += f"\n*Data as of: {data_as_of}*\n"
    header += "\n"

    sections = [
        header,
        compute_deck_overview(cards, deck_stats),
        compute_interest_heat(cards, top_n=top_n),
        compute_study_consistency(review_day_map),
    ]
    return "\n".join(sections)
