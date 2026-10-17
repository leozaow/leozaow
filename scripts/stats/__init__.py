"""Statistics and streak calculation package for GitHub profile."""

from scripts.stats.models import (
    ActivityBar,
    ContributionDay,
    StreakInterval,
    StreakStats,
)
from scripts.stats.calculations import (
    calculate_streak_stats,
    reference_calculate_streaks,
)
from scripts.stats.renderer import render_streak_svg

__all__ = [
    "ActivityBar",
    "ContributionDay",
    "StreakInterval",
    "StreakStats",
    "calculate_streak_stats",
    "reference_calculate_streaks",
    "render_streak_svg",
]
