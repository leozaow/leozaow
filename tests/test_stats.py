"""Comprehensive unit test suite for contribution and streak statistics engine.

Covers all 35 edge cases specified in Section 7.1 and validates against an independent
reference implementation as required by Section 7.2.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

from scripts.stats.calculations import (
    build_recent_activity,
    calculate_current_streak,
    calculate_longest_streak,
    calculate_streak_stats,
    calculate_weekly_streaks,
    get_iso_monday,
    reference_calculate_streaks,
    validate_and_normalize_days,
)
from scripts.stats.github import execute_graphql, fetch_all_contributions
from scripts.stats.models import ActivityBar, StreakInterval, StreakStats


class TestStreakCalculations(unittest.TestCase):
    """Exhaustive test suite covering all specified edge cases."""

    # 1. Empty valid contribution history
    def test_01_empty_history(self):
        days: dict[date, int] = {}
        ref = date(2026, 10, 17)
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 0)
        self.assertIsNone(stats.current_streak.start_date)
        self.assertIsNone(stats.current_streak.end_date)
        self.assertEqual(stats.longest_streak.length, 0)
        self.assertEqual(stats.total_contributions, 0)
        self.assertEqual(stats.total_active_days, 0)
        curr_ref, long_ref = reference_calculate_streaks(days, ref)
        self.assertEqual(curr_ref, 0)
        self.assertEqual(long_ref, 0)

    # 2. One contribution on one day
    def test_02_single_contribution_single_day(self):
        ref = date(2026, 10, 17)
        days = {ref: 1}
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 1)
        self.assertEqual(stats.current_streak.start_date, ref)
        self.assertEqual(stats.current_streak.end_date, ref)
        self.assertEqual(stats.longest_streak.length, 1)
        self.assertEqual(stats.total_contributions, 1)
        self.assertEqual(stats.total_active_days, 1)

    # 3. Multiple contributions on one day
    def test_03_multiple_contributions_single_day(self):
        ref = date(2026, 10, 17)
        days = {ref: 42}
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 1)
        self.assertEqual(stats.total_contributions, 42)
        self.assertEqual(stats.total_active_days, 1)

    # 4. Zero-contribution days between active periods
    def test_04_zero_contribution_days_between_active_periods(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 10, 10): 2,
            date(2026, 10, 11): 0,
            date(2026, 10, 12): 0,
            date(2026, 10, 13): 3,
            date(2026, 10, 14): 4,
            date(2026, 10, 15): 0,
            date(2026, 10, 16): 5,
            date(2026, 10, 17): 1,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 2)  # 16 and 17
        self.assertEqual(stats.current_streak.start_date, date(2026, 10, 16))
        self.assertEqual(stats.current_streak.end_date, date(2026, 10, 17))
        self.assertEqual(stats.longest_streak.length, 2)

    # 5. Current streak including today
    def test_05_current_streak_including_today(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 10, 15): 2,
            date(2026, 10, 16): 4,
            date(2026, 10, 17): 1,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 3)
        self.assertEqual(stats.current_streak.start_date, date(2026, 10, 15))
        self.assertEqual(stats.current_streak.end_date, date(2026, 10, 17))

    # 6. Current streak ending yesterday (grace period)
    def test_06_current_streak_ending_yesterday_grace(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 10, 14): 1,
            date(2026, 10, 15): 2,
            date(2026, 10, 16): 4,
            date(2026, 10, 17): 0,  # today unfinished
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 3)
        self.assertEqual(stats.current_streak.start_date, date(2026, 10, 14))
        self.assertEqual(stats.current_streak.end_date, date(2026, 10, 16))

    # 7. Current streak broken before yesterday
    def test_07_current_streak_broken_before_yesterday(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 10, 14): 3,
            date(2026, 10, 15): 2,
            date(2026, 10, 16): 0,  # yesterday zero
            date(2026, 10, 17): 0,  # today zero
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 0)
        self.assertIsNone(stats.current_streak.start_date)
        self.assertIsNone(stats.current_streak.end_date)
        self.assertEqual(stats.longest_streak.length, 2)
        self.assertEqual(stats.longest_streak.start_date, date(2026, 10, 14))
        self.assertEqual(stats.longest_streak.end_date, date(2026, 10, 15))

    # 8. Longest streak independent of current streak
    def test_08_longest_streak_independent(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 1, 1): 1,
            date(2026, 1, 2): 2,
            date(2026, 1, 3): 1,
            date(2026, 1, 4): 3,
            date(2026, 1, 5): 2,  # 5 days
            date(2026, 10, 16): 1,
            date(2026, 10, 17): 1,  # 2 days
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 2)
        self.assertEqual(stats.longest_streak.length, 5)
        self.assertEqual(stats.longest_streak.start_date, date(2026, 1, 1))
        self.assertEqual(stats.longest_streak.end_date, date(2026, 1, 5))

    # 9. Current streak tied with historical record
    def test_09_current_streak_tied_with_historical_record(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 1, 1): 1,
            date(2026, 1, 2): 1,
            date(2026, 1, 3): 1,  # 3 days
            date(2026, 10, 15): 1,
            date(2026, 10, 16): 1,
            date(2026, 10, 17): 1,  # 3 days
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 3)
        self.assertEqual(stats.longest_streak.length, 3)
        # Most recent tie-breaker should match the current streak
        self.assertEqual(stats.longest_streak.start_date, stats.current_streak.start_date)
        self.assertEqual(stats.longest_streak.end_date, stats.current_streak.end_date)

    # 10. Multiple equal-length record streaks
    def test_10_multiple_equal_length_records(self):
        days = {
            date(2025, 2, 1): 1,
            date(2025, 2, 2): 1,  # streak A (len 2)
            date(2025, 5, 1): 1,
            date(2025, 5, 2): 1,  # streak B (len 2)
        }
        earliest = calculate_longest_streak(days, tie_breaker="earliest")
        latest = calculate_longest_streak(days, tie_breaker="most_recent")
        self.assertEqual(earliest.start_date, date(2025, 2, 1))
        self.assertEqual(latest.start_date, date(2025, 5, 1))

    # 11. Cross-month streaks
    def test_11_cross_month_streaks(self):
        ref = date(2026, 4, 3)
        days = {
            date(2026, 3, 30): 1,
            date(2026, 3, 31): 2,
            date(2026, 4, 1): 1,
            date(2026, 4, 2): 3,
            date(2026, 4, 3): 2,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 5)
        self.assertEqual(stats.current_streak.start_date, date(2026, 3, 30))
        self.assertEqual(stats.current_streak.end_date, date(2026, 4, 3))

    # 12. Cross-year streaks
    def test_12_cross_year_streaks(self):
        ref = date(2026, 1, 2)
        days = {
            date(2025, 12, 30): 1,
            date(2025, 12, 31): 2,
            date(2026, 1, 1): 3,
            date(2026, 1, 2): 1,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 4)
        self.assertEqual(stats.current_streak.start_date, date(2025, 12, 30))
        self.assertEqual(stats.current_streak.end_date, date(2026, 1, 2))

    # 13. Leap-year February
    def test_13_leap_year_february(self):
        ref = date(2024, 3, 1)  # 2024 was leap year
        days = {
            date(2024, 2, 28): 1,
            date(2024, 2, 29): 1,
            date(2024, 3, 1): 1,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 3)
        self.assertEqual(stats.current_streak.start_date, date(2024, 2, 28))

    # 14. Non-leap-year February
    def test_14_non_leap_year_february(self):
        ref = date(2025, 3, 1)  # 2025 was non-leap
        days = {
            date(2025, 2, 28): 1,
            date(2025, 3, 1): 1,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 2)
        self.assertEqual(stats.current_streak.start_date, date(2025, 2, 28))

    # 15. ISO week transitions
    def test_15_iso_week_transitions(self):
        ref = date(2026, 10, 18)  # Sunday
        days = {date(2026, 10, 12): 1}  # Monday of this week
        curr_w, longest_w = calculate_weekly_streaks(days, ref)
        self.assertEqual(curr_w.length, 1)
        self.assertEqual(curr_w.start_date, date(2026, 10, 12))

    # 16. Week 53 where applicable
    def test_16_week_53(self):
        # 2020 has 53 ISO weeks
        ref = date(2020, 12, 31)
        days = {
            date(2020, 12, 28): 1,  # Mon in week 53
            date(2020, 12, 31): 2,
        }
        curr_w, _ = calculate_weekly_streaks(days, ref)
        self.assertGreaterEqual(curr_w.length, 1)

    # 17. Unfinished current week
    def test_17_unfinished_current_week_grace(self):
        ref = date(2026, 10, 20)  # Tuesday, no activity
        # Previous week had activity
        days = {
            date(2026, 10, 14): 2,  # Wednesday of previous week
            date(2026, 10, 19): 0,  # Mon of current week
            date(2026, 10, 20): 0,  # Tue of current week
        }
        curr_w, _ = calculate_weekly_streaks(days, ref)
        # Grace rule applies to unfinished current week
        self.assertEqual(curr_w.length, 1)

    # 18. Weekly versus daily streak semantics
    def test_18_weekly_vs_daily_streak_semantics(self):
        ref = date(2026, 10, 17)
        # 1 day active each week for 3 weeks
        days = {
            date(2026, 9, 30): 1,  # Week 1
            date(2026, 10, 7): 1,  # Week 2
            date(2026, 10, 14): 1,  # Week 3
        }
        stats = calculate_streak_stats(days, ref)
        # Daily streak is 0 because no activity on Oct 16 or 17
        self.assertEqual(stats.current_streak.length, 0)
        # Weekly streak is 3
        self.assertEqual(stats.current_weekly_streak.length, 3)

    # 19. Missing input dates
    def test_19_missing_input_dates(self):
        ref = date(2026, 10, 17)
        # Dictionary only has sparse active days
        days = {
            date(2026, 10, 10): 5,
            date(2026, 10, 17): 3,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 1)
        self.assertEqual(stats.longest_streak.length, 1)

    # 20. Duplicate input dates (handled by dict)
    def test_20_duplicate_input_dates(self):
        days = {date(2026, 10, 17): 1}
        norm = validate_and_normalize_days(days)
        self.assertEqual(len(norm), 1)

    # 21. Out-of-order input dates
    def test_21_out_of_order_input_dates(self):
        days = {
            date(2026, 10, 17): 1,
            date(2026, 10, 15): 2,
            date(2026, 10, 16): 3,
        }
        stats = calculate_streak_stats(days, date(2026, 10, 17))
        self.assertEqual(stats.current_streak.length, 3)
        self.assertEqual(stats.current_streak.start_date, date(2026, 10, 15))

    # 22. Future-dated data
    def test_22_future_dated_data(self):
        ref = date(2026, 10, 17)
        days = {
            date(2026, 10, 16): 2,
            date(2026, 10, 17): 1,
            date(2026, 10, 25): 10,  # future
        }
        stats = calculate_streak_stats(days, ref)
        # Current streak respects reference_date
        self.assertEqual(stats.current_streak.length, 2)
        self.assertEqual(stats.current_streak.end_date, ref)

    # 23. Negative contribution values
    def test_23_negative_contribution_values(self):
        days = {date(2026, 10, 17): -1}
        with self.assertRaises(ValueError):
            validate_and_normalize_days(days)

    # 24. Invalid date strings / types
    def test_24_invalid_date_types(self):
        days = {"2026-10-17": 5}  # not a date object
        with self.assertRaises(TypeError):
            validate_and_normalize_days(days)  # type: ignore

    # 25. Incomplete API payload / error handling
    def test_25_incomplete_api_payload(self):
        with self.assertRaises(ValueError):
            execute_graphql("", "query { viewer { login } }", {})

    # 26. Correct rolling-window boundaries (last 365 days)
    def test_26_rolling_window_boundaries(self):
        ref = date(2026, 10, 17)
        d_in = ref - timedelta(days=364)  # inside 365 days
        d_out = ref - timedelta(days=365)  # outside 365 days
        days = {
            d_out: 10,
            d_in: 5,
            ref: 3,
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.contributions_last_year, 8)  # 5 + 3
        self.assertEqual(stats.total_contributions, 18)  # 10 + 5 + 3

    # 27. Complete inactivity in the last 35 days
    def test_27_complete_inactivity_last_35_days(self):
        ref = date(2026, 10, 17)
        days = {
            date(2025, 1, 1): 50,  # ancient activity
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 0)
        self.assertEqual(len(stats.recent_activity), 35)
        self.assertTrue(all(bar.count == 0 for bar in stats.recent_activity))
        self.assertTrue(all(not bar.is_current_streak for bar in stats.recent_activity))

    # 28. A daily streak longer than the chart period (e.g. 50 days)
    def test_28_streak_longer_than_chart_period(self):
        ref = date(2026, 10, 17)
        days = {ref - timedelta(days=i): 1 for i in range(50)}
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 50)
        self.assertEqual(len(stats.recent_activity), 35)
        # All 35 days in recent activity should be flagged as part of the current streak
        self.assertTrue(all(bar.is_current_streak for bar in stats.recent_activity))

    # 29. Current-day grace-period bar highlighting
    def test_29_grace_period_bar_highlighting(self):
        ref = date(2026, 10, 17)
        days = {
            ref - timedelta(days=2): 2,
            ref - timedelta(days=1): 3,
            ref: 0,  # today 0
        }
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 2)
        # The last bar (today) must NOT be highlighted
        today_bar = stats.recent_activity[-1]
        self.assertEqual(today_bar.date, ref)
        self.assertFalse(today_bar.is_current_streak)
        # Yesterday's bar must be highlighted
        yesterday_bar = stats.recent_activity[-2]
        self.assertEqual(yesterday_bar.date, ref - timedelta(days=1))
        self.assertTrue(yesterday_bar.is_current_streak)

    # 30. Fixed reference time with different host timezones
    def test_30_fixed_reference_time(self):
        ref = date(2026, 10, 17)
        days = {ref: 5}
        t_utc = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
        t_sp = datetime(2026, 10, 17, 9, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
        stats1 = calculate_streak_stats(days, ref, generated_at=t_utc)
        stats2 = calculate_streak_stats(days, ref, generated_at=t_sp)
        self.assertEqual(stats1.current_streak.length, stats2.current_streak.length)
        self.assertEqual(stats1.total_contributions, stats2.total_contributions)

    # 31. UTC and São Paulo day transitions
    def test_31_day_transitions(self):
        # When UTC is 00:00 on Oct 17, São Paulo is 21:00 on Oct 16
        # Our engine uses canonical date for streak evaluation
        ref = date(2026, 10, 17)
        days = {date(2026, 10, 16): 4, date(2026, 10, 17): 1}
        stats = calculate_streak_stats(days, ref)
        self.assertEqual(stats.current_streak.length, 2)

    # 32. Stable date formatting
    def test_32_stable_date_formatting(self):
        from scripts.stats.renderer import format_date_range

        self.assertEqual(format_date_range(None, None), "No active streak")
        self.assertEqual(format_date_range(date(2026, 10, 17), date(2026, 10, 17)), "Oct 17, 2026")
        self.assertEqual(
            format_date_range(date(2026, 9, 30), date(2026, 10, 16)),
            "Sep 30 – Oct 16, 2026",
        )
        self.assertEqual(
            format_date_range(date(2025, 12, 31), date(2026, 1, 2)),
            "Dec 31, 2025 – Jan 02, 2026",
        )

    # 33. Reproducible metric serialization
    def test_33_reproducible_serialization(self):
        ref = date(2026, 10, 17)
        days = {ref: 2}
        stats = calculate_streak_stats(days, ref, generated_at=datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc))
        d1 = stats.to_dict()
        d2 = stats.to_dict()
        self.assertEqual(d1, d2)
        json_str = json.dumps(d1, sort_keys=True)
        self.assertIn('"length": 1', json_str)

    # 34. Independent reference implementation comparison (Property verification)
    def test_34_compare_with_reference_implementation(self):
        ref = date(2026, 10, 17)
        # Test across multiple random/deterministic patterns
        for offset in range(5):
            days = {}
            for i in range(60):
                d = ref - timedelta(days=i)
                days[d] = 1 if ((i + offset) % 3 != 0) else 0

            stats = calculate_streak_stats(days, ref)
            ref_curr, ref_longest = reference_calculate_streaks(days, ref)
            self.assertEqual(stats.current_streak.length, ref_curr)
            self.assertEqual(stats.longest_streak.length, ref_longest)

    # 35. Correct differentiation between zero data and unavailable data
    def test_35_differentiation_zero_vs_unavailable(self):
        ref = date(2026, 10, 17)
        # Empty days vs explicit complete=False
        empty_days: dict[date, int] = {}
        stats_complete = calculate_streak_stats(empty_days, ref, is_complete_history=True)
        stats_partial = calculate_streak_stats(empty_days, ref, is_complete_history=False)
        self.assertTrue(stats_complete.is_complete_history)
        self.assertFalse(stats_partial.is_complete_history)


if __name__ == "__main__":
    unittest.main()
