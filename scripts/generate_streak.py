#!/usr/bin/env python3
"""CLI tool to fetch GitHub contribution data and generate accessible streak SVGs.

Uses the scripts.stats engine to compute mathematically sound daily/weekly streaks,
generate responsive and accessible light/dark SVGs, and emit JSON diagnostics.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional
from zoneinfo import ZoneInfo

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.stats.calculations import calculate_streak_stats
from scripts.stats.github import (
    fetch_account_created_at,
    fetch_all_contributions,
    fetch_contributions_chunk,
)
from scripts.stats.models import StreakStats
from scripts.stats.renderer import render_streak_svg

DEFAULT_TZ = ZoneInfo("America/Sao_Paulo")
logger = logging.getLogger("generate_streak")


def generate_demo_days(reference_date: date) -> Dict[date, int]:
    """Generates a deterministic 540-day contribution fixture for local testing."""
    days: Dict[date, int] = {}
    for i in range(540):
        d = reference_date - timedelta(days=539 - i)
        v = (i * 7 + i // 9) % 11
        days[d] = 0 if v < 4 else (v - 3)
    # Add an active current streak for testing
    for i in range(1, 15):
        days[reference_date - timedelta(days=i)] = 2 + (i % 4)
    # Reference date itself has 0 (demonstrating current-day grace rule)
    days[reference_date] = 0
    return days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate self-hosted GitHub streak SVG cards.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "assets",
        help="Directory where SVG cards and stats.json will be saved (default: assets/)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate cards using deterministic mock data without querying the GitHub API.",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_USER") or "leozaow",
        help="Target GitHub username (default: leozaow)",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="Freeze reference date (YYYY-MM-DD) for deterministic testing.",
    )
    parser.add_argument(
        "--write-json",
        action="store_true",
        default=True,
        help="Write machine-readable stats.json diagnostic file (default: True).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.reference_date:
        ref_date = date.fromisoformat(args.reference_date)
    else:
        ref_date = datetime.now(DEFAULT_TZ).date()

    if args.demo:
        days = generate_demo_days(ref_date)
        is_complete = True
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN environment variable is required when --demo is not set.", file=sys.stderr)
            return 1

        try:
            created_at = fetch_account_created_at(token, args.username)
            days, _ = fetch_all_contributions(token, args.username, created_at, ref_date)
            is_complete = True
        except Exception as e:
            logger.warning("Historical fetch failed (%s); falling back to rolling 1-year window", e)
            year_start = ref_date - timedelta(days=364)
            days, _ = fetch_contributions_chunk(token, args.username, year_start, ref_date)
            is_complete = False

    stats = calculate_streak_stats(
        days=days,
        reference_date=ref_date,
        username=args.username,
        is_complete_history=is_complete,
    )

    # Render SVGs for light and dark themes
    for theme in ("light", "dark"):
        svg_content = render_streak_svg(stats, theme=theme)
        out_file = output_dir / f"streak.{theme}.svg"
        out_file.write_text(svg_content, encoding="utf-8")

    # Diagnostic JSON
    if args.write_json:
        json_file = output_dir / "stats.json"
        json_file.write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")

    print(
        f"current_days={stats.current_streak.length} longest_days={stats.longest_streak.length} "
        f"current_weeks={stats.current_weekly_streak.length} longest_weeks={stats.longest_weekly_streak.length} "
        f"total={stats.total_contributions} active_days={stats.total_active_days}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
