"""Canonical data models for GitHub contributions and streak analytics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ContributionDay:
    """Represents activity on a specific calendar day."""

    date: date
    count: int
    level: str = "NONE"


@dataclass(frozen=True)
class StreakInterval:
    """Represents a continuous streak interval with start and end dates."""

    length: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @property
    def is_active(self) -> bool:
        return self.length > 0 and self.start_date is not None and self.end_date is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "length": self.length,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


@dataclass(frozen=True)
class ActivityBar:
    """Represents an individual bar in the recent activity chart."""

    date: date
    count: int
    is_current_streak: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "count": self.count,
            "is_current_streak": self.is_current_streak,
        }


@dataclass
class StreakStats:
    """Comprehensive calculated contribution statistics and view model."""

    # Daily Streaks
    current_streak: StreakInterval
    longest_streak: StreakInterval

    # Weekly Streaks (ISO Monday-Sunday)
    current_weekly_streak: StreakInterval
    longest_weekly_streak: StreakInterval

    # Contribution Totals
    contributions_last_year: int
    active_days_last_year: int
    total_contributions: int
    total_active_days: int

    # Temporal Bounds
    history_start: Optional[date]
    history_end: Optional[date]
    reference_date: date
    generated_at: datetime

    # Recent Activity Series (e.g. 35 days)
    recent_activity: List[ActivityBar]

    # Data provenance metadata
    is_complete_history: bool = True
    username: str = "leozaow"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "reference_date": self.reference_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "is_complete_history": self.is_complete_history,
            "current_streak": self.current_streak.to_dict(),
            "longest_streak": self.longest_streak.to_dict(),
            "weekly_streaks": {
                "current": self.current_weekly_streak.to_dict(),
                "longest": self.longest_weekly_streak.to_dict(),
            },
            "contributions_last_year": self.contributions_last_year,
            "active_days_last_year": self.active_days_last_year,
            "total_contributions": self.total_contributions,
            "total_active_days": self.total_active_days,
            "history_start": self.history_start.isoformat() if self.history_start else None,
            "history_end": self.history_end.isoformat() if self.history_end else None,
            "recent_activity_days": [bar.to_dict() for bar in self.recent_activity],
        }
