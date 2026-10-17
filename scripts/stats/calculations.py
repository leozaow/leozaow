"""Pure mathematical functions for contribution streaks and activity calculations."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from scripts.stats.models import (
    ActivityBar,
    StreakInterval,
    StreakStats,
)


def validate_and_normalize_days(raw_days: Dict[date, int]) -> Dict[date, int]:
    """Validates contribution counts and returns sorted, sanitized date-to-count mapping."""
    if not isinstance(raw_days, dict):
        raise TypeError("raw_days must be a dictionary of date to integer counts")

    normalized: Dict[date, int] = {}
    for d, count in raw_days.items():
        if not isinstance(d, date):
            raise TypeError(f"Invalid date key: {d!r}")
        if count < 0:
            raise ValueError(f"Contribution count cannot be negative: {count} on {d}")
        normalized[d] = int(count)

    return dict(sorted(normalized.items()))


def calculate_current_streak(
    days: Dict[date, int],
    reference_date: date,
) -> StreakInterval:
    """Calculates the current unbroken daily streak respecting the current-day grace rule.

    Semantics:
    1. A calendar day qualifies if contributions > 0.
    2. If reference_date qualifies, the streak ends on reference_date.
    3. If reference_date does not qualify (e.g. unfinished day with 0 contributions so far),
       but yesterday qualifies, the streak ending yesterday is preserved as the active streak.
    4. If neither reference_date nor yesterday qualifies, the current streak is 0.
    5. The reported start_date and end_date strictly match the actual counted qualifying days.
    """
    today_count = days.get(reference_date, 0)
    yesterday = reference_date - timedelta(days=1)
    yesterday_count = days.get(yesterday, 0)

    if today_count > 0:
        end_date = reference_date
    elif yesterday_count > 0:
        end_date = yesterday
    else:
        return StreakInterval(length=0, start_date=None, end_date=None)

    # Walk backwards from end_date
    cursor = end_date
    length = 0
    while days.get(cursor, 0) > 0:
        length += 1
        cursor -= timedelta(days=1)

    start_date = cursor + timedelta(days=1)
    return StreakInterval(length=length, start_date=start_date, end_date=end_date)


def calculate_longest_streak(
    days: Dict[date, int],
    tie_breaker: str = "most_recent",
) -> StreakInterval:
    """Calculates the maximum consecutive run of qualifying days in historical data.

    Args:
        days: Normalized mapping of date to contribution count.
        tie_breaker: 'most_recent' favors the latest occurrence, 'earliest' favors the first.
    """
    if not days:
        return StreakInterval(length=0, start_date=None, end_date=None)

    qualifying_dates = sorted([d for d, count in days.items() if count > 0])
    if not qualifying_dates:
        return StreakInterval(length=0, start_date=None, end_date=None)

    streaks: List[StreakInterval] = []
    run_start = qualifying_dates[0]
    run_prev = qualifying_dates[0]
    run_length = 1

    for d in qualifying_dates[1:]:
        if d == run_prev + timedelta(days=1):
            run_length += 1
            run_prev = d
        else:
            streaks.append(StreakInterval(length=run_length, start_date=run_start, end_date=run_prev))
            run_start = d
            run_prev = d
            run_length = 1

    streaks.append(StreakInterval(length=run_length, start_date=run_start, end_date=run_prev))

    max_len = max(s.length for s in streaks)
    matching = [s for s in streaks if s.length == max_len]

    if tie_breaker == "earliest":
        return matching[0]
    return matching[-1]


def get_iso_monday(d: date) -> date:
    """Returns the Monday of the ISO week containing date d."""
    return d - timedelta(days=d.weekday())


def is_week_active(days: Dict[date, int], monday: date) -> bool:
    """Returns True if any day from Monday through Sunday in this week has contributions > 0."""
    return any(days.get(monday + timedelta(days=i), 0) > 0 for i in range(7))


def calculate_weekly_streaks(
    days: Dict[date, int],
    reference_date: date,
) -> Tuple[StreakInterval, StreakInterval]:
    """Calculates current and longest weekly streaks based on ISO week boundaries."""
    if not days:
        empty = StreakInterval(length=0, start_date=None, end_date=None)
        return empty, empty

    min_date = min(days.keys())
    first_monday = get_iso_monday(min_date)
    ref_monday = get_iso_monday(reference_date)

    mondays: List[date] = []
    curr = first_monday
    while curr <= ref_monday:
        mondays.append(curr)
        curr += timedelta(days=7)

    if not mondays:
        empty = StreakInterval(length=0, start_date=None, end_date=None)
        return empty, empty

    # Longest weekly streak
    runs: List[StreakInterval] = []
    curr_start: Optional[date] = None
    curr_prev: Optional[date] = None
    curr_len = 0

    for m in mondays:
        if is_week_active(days, m):
            if curr_len == 0:
                curr_start = m
            curr_len += 1
            curr_prev = m
        else:
            if curr_len > 0 and curr_start and curr_prev:
                runs.append(
                    StreakInterval(
                        length=curr_len,
                        start_date=curr_start,
                        end_date=curr_prev + timedelta(days=6),
                    )
                )
            curr_len = 0
            curr_start = None
            curr_prev = None

    if curr_len > 0 and curr_start and curr_prev:
        runs.append(
            StreakInterval(
                length=curr_len,
                start_date=curr_start,
                end_date=curr_prev + timedelta(days=6),
            )
        )

    longest = (
        max(runs, key=lambda s: s.length)
        if runs
        else StreakInterval(length=0, start_date=None, end_date=None)
    )

    # Current weekly streak with grace rule for unfinished week
    curr_week_active = is_week_active(days, ref_monday)
    prev_monday = ref_monday - timedelta(days=7)
    prev_week_active = is_week_active(days, prev_monday) if prev_monday >= first_monday else False

    if curr_week_active:
        end_idx = len(mondays) - 1
        end_date = min(reference_date, mondays[end_idx] + timedelta(days=6))
    elif prev_week_active:
        end_idx = len(mondays) - 2
        end_date = mondays[end_idx] + timedelta(days=6)
    else:
        current_weekly = StreakInterval(length=0, start_date=None, end_date=None)
        return current_weekly, longest

    count = 0
    start_date = None
    for i in range(end_idx, -1, -1):
        m = mondays[i]
        if is_week_active(days, m):
            count += 1
            start_date = m
        else:
            break

    current_weekly = StreakInterval(length=count, start_date=start_date, end_date=end_date)
    return current_weekly, longest


def build_recent_activity(
    days: Dict[date, int],
    reference_date: date,
    window_days: int = 35,
    current_streak: Optional[StreakInterval] = None,
) -> List[ActivityBar]:
    """Constructs the recent daily activity series with accurate streak date membership."""
    start_date = reference_date - timedelta(days=window_days - 1)
    bars: List[ActivityBar] = []

    for i in range(window_days):
        d = start_date + timedelta(days=i)
        count = days.get(d, 0)
        is_in_streak = False
        if current_streak and current_streak.is_active:
            if current_streak.start_date and current_streak.end_date:
                is_in_streak = current_streak.start_date <= d <= current_streak.end_date and count > 0

        bars.append(ActivityBar(date=d, count=count, is_current_streak=is_in_streak))

    return bars


def calculate_streak_stats(
    days: Dict[date, int],
    reference_date: date,
    username: str = "leozaow",
    window_days: int = 35,
    generated_at: Optional[datetime] = None,
    is_complete_history: bool = True,
) -> StreakStats:
    """Calculates all metrics deterministically from normalized contribution data."""
    norm_days = validate_and_normalize_days(days)
    gen_time = generated_at or datetime.now(timezone.utc)

    current_daily = calculate_current_streak(norm_days, reference_date)
    longest_daily = calculate_longest_streak(norm_days, tie_breaker="most_recent")

    # If current daily streak equals or exceeds longest, synchronize them
    if current_daily.is_active and current_daily.length >= longest_daily.length:
        longest_daily = current_daily

    current_weekly, longest_weekly = calculate_weekly_streaks(norm_days, reference_date)

    # Rolling last 365 days calculations
    year_start = reference_date - timedelta(days=364)
    last_year_days = {d: c for d, c in norm_days.items() if year_start <= d <= reference_date}
    contributions_last_year = sum(last_year_days.values())
    active_days_last_year = sum(1 for c in last_year_days.values() if c > 0)

    # All-time / total queried dataset calculations
    total_contributions = sum(norm_days.values())
    total_active_days = sum(1 for c in norm_days.values() if c > 0)

    history_start = min(norm_days.keys()) if norm_days else None
    history_end = max(norm_days.keys()) if norm_days else None

    recent_activity = build_recent_activity(
        norm_days,
        reference_date,
        window_days=window_days,
        current_streak=current_daily,
    )

    return StreakStats(
        current_streak=current_daily,
        longest_streak=longest_daily,
        current_weekly_streak=current_weekly,
        longest_weekly_streak=longest_weekly,
        contributions_last_year=contributions_last_year,
        active_days_last_year=active_days_last_year,
        total_contributions=total_contributions,
        total_active_days=total_active_days,
        history_start=history_start,
        history_end=history_end,
        reference_date=reference_date,
        generated_at=gen_time,
        recent_activity=recent_activity,
        is_complete_history=is_complete_history,
        username=username,
    )


# ---------------------------------------------------------------------------
# Independent simple reference implementation for test verification
# ---------------------------------------------------------------------------

def reference_calculate_streaks(
    days: Dict[date, int],
    reference_date: date,
) -> Tuple[int, int]:
    """A completely straightforward, unoptimized reference implementation.

    Used strictly in tests to independently verify the production algorithm.
    Returns (current_streak_length, longest_streak_length).
    """
    if not days:
        return 0, 0

    # Current streak
    curr = reference_date
    if days.get(curr, 0) == 0:
        curr -= timedelta(days=1)

    curr_len = 0
    while days.get(curr, 0) > 0:
        curr_len += 1
        curr -= timedelta(days=1)

    # Longest streak via exhaustive day-by-day continuous walk
    all_dates = sorted(days.keys())
    if not all_dates:
        return curr_len, 0

    max_len = 0
    cur_walk = 0
    min_d = all_dates[0]
    max_d = all_dates[-1]

    d = min_d
    while d <= max_d:
        if days.get(d, 0) > 0:
            cur_walk += 1
            if cur_walk > max_len:
                max_len = cur_walk
        else:
            cur_walk = 0
        d += timedelta(days=1)

    return curr_len, max_len
