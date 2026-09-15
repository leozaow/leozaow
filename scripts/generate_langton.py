#!/usr/bin/env python3
"""CLI tool to fetch GitHub contribution data and generate Langton's Ant SVGs (V4).

Supports production mode (GraphQL) and fixture mode, deep multi-thousand step simulation,
sliding window discovery, and deterministic daily variability controlled by date and calendar seed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.langton_sim import (
    CalendarData,
    SimulationResult,
    parse_contribution_calendar,
)
from scripts.langton_analysis import DeepAnalysis, select_daily_simulation
from scripts.langton_render import render_langton_svg_v3

API_URL = "https://api.github.com/graphql"
DEFAULT_TZ = ZoneInfo("America/Sao_Paulo")

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


def fetch_contributions_graphql(token: str, username: str) -> dict:
    """Queries GitHub GraphQL API for the user's contribution calendar."""
    body = json.dumps({"query": GRAPHQL_QUERY, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "leozaow-langton-renderer-v4",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    if payload.get("errors"):
        err_msg = json.dumps(payload["errors"], ensure_ascii=False)
        raise RuntimeError(f"GitHub GraphQL error: {err_msg}")

    user_data = payload.get("data", {}).get("user")
    if not user_data:
        raise ValueError(f"GitHub user '{username}' not found or no data returned.")

    return payload


def generate_all(
    calendar_payload: dict,
    output_dir: Path,
    date_str: str,
    steps_count: int = 240,
    deep_horizon: int = 10000,
    pool_capacity: int = 12,
    duration_s: float = 16.0,
    debug_json: bool = False,
    dry_run: bool = False,
) -> Tuple[Path, Path]:
    """Runs deep simulation and outputs the V4 light and dark SVGs."""
    calendar = parse_contribution_calendar(calendar_payload)
    simulation, analysis = select_daily_simulation(
        calendar=calendar,
        date_str=date_str,
        steps_count=steps_count,
        deep_horizon=deep_horizon,
        pool_capacity=pool_capacity,
    )

    svg_light = render_langton_svg_v3(
        calendar=calendar,
        simulation=simulation,
        analysis=analysis,
        theme="light",
        duration_s=duration_s,
    )
    svg_dark = render_langton_svg_v3(
        calendar=calendar,
        simulation=simulation,
        analysis=analysis,
        theme="dark",
        duration_s=duration_s,
    )

    light_path = output_dir / "langton-contribution-graph.svg"
    dark_path = output_dir / "langton-contribution-graph-dark.svg"

    active_days = sum(1 for c in calendar.cells.values() if c.count > 0)
    visible_in_cal = sum(1 for s in simulation.steps if 0 <= s.x < calendar.weeks_count and 0 <= s.y < 7)

    print("=== Langton's Ant V4 Generation Telemetry ===")
    print(f"totalContributions:              {calendar.total_contributions}")
    print(f"activeDays:                      {active_days}")
    print(f"calendarStart:                   {calendar.min_date}")
    print(f"calendarEnd:                     {calendar.max_date}")
    print(f"targetDate:                      {date_str}")
    print(f"dailySeed:                       {analysis.daily_seed[:16]}...")
    print(f"candidatePoolSize:               {analysis.pool_size}")
    print(f"selectedCandidateRank:           #{analysis.selected_rank + 1} of {analysis.pool_size}")
    print(f"startPosition:                   W{simulation.start_x:02d}:D{simulation.start_y}")
    print(f"startDirection:                  {simulation.start_dir} [{analysis.candidate_direction}]")
    print(f"windowSlice:                     steps [{simulation.window_start}..{simulation.window_end}]")
    print(f"deepHorizonSimulated:            {analysis.total_simulated}")
    print(f"visibleSteps:                    {visible_in_cal}")
    print(f"uniqueVisited:                   {len(simulation.visited_cells)}")
    print(f"activeContributionCellsVisited:  {analysis.commits_visited}")
    print(f"highwayDetected:                 {analysis.highway_detected}")
    if analysis.highway_detected:
        print(f"highwayPeriod:                   {analysis.highway_period}")
        print(f"highwayVector:                   ({analysis.highway_dx}, {analysis.highway_dy})")
        print(f"highwayVerifiedCycles:           {analysis.highway_verified_cycles}")
        if analysis.highway_start_step is not None:
            print(f"highwayStartStep:                {analysis.highway_start_step}")
    print("=============================================")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        light_path.write_text(svg_light, encoding="utf-8")
        dark_path.write_text(svg_dark, encoding="utf-8")

        if debug_json:
            debug_info = {
                "version": 4,
                "calendar": {
                    "totalContributions": calendar.total_contributions,
                    "activeDays": active_days,
                    "calendarStart": calendar.min_date,
                    "calendarEnd": calendar.max_date,
                },
                "selection": {
                    "targetDate": date_str,
                    "dailySeed": analysis.daily_seed,
                    "poolSize": analysis.pool_size,
                    "selectedRank": analysis.selected_rank,
                    "origin": {"x": simulation.start_x, "y": simulation.start_y},
                    "direction": analysis.candidate_direction,
                    "windowStart": simulation.window_start,
                    "windowEnd": simulation.window_end,
                },
                "simulation": {
                    "deepHorizonSimulated": analysis.total_simulated,
                    "displaySteps": steps_count,
                    "visibleSteps": visible_in_cal,
                    "uniqueVisited": len(simulation.visited_cells),
                    "activeContributionCellsVisited": analysis.commits_visited,
                    "boundingBox": {
                        "min_x": analysis.bounding_box[0],
                        "max_x": analysis.bounding_box[1],
                        "min_y": analysis.bounding_box[2],
                        "max_y": analysis.bounding_box[3],
                    },
                },
                "highway": {
                    "detected": analysis.highway_detected,
                    "period": analysis.highway_period,
                    "vector": [analysis.highway_dx, analysis.highway_dy],
                    "verifiedCycles": analysis.highway_verified_cycles,
                    "startEstimate": analysis.highway_start_step,
                },
                "phases": [
                    {
                        "start": p.start_step,
                        "end": p.end_step,
                        "name": p.name,
                        "in_bounds_ratio": round(p.in_bounds_ratio, 3),
                        "commits_ratio": round(p.commits_ratio, 3),
                        "entropy": round(p.entropy, 3),
                    }
                    for p in analysis.phases
                ],
            }
            (output_dir / "langton-debug.json").write_text(json.dumps(debug_info, indent=2), encoding="utf-8")

    return light_path, dark_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Langton's Ant contribution SVGs V4.")
    parser.add_argument("--input", "-i", type=Path, help="Path to input JSON fixture.")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("dist"), help="Directory to save SVGs.")
    parser.add_argument("--username", "-u", type=str, help="GitHub username.")
    parser.add_argument("--date", "-d", type=str, help="Date string YYYY-MM-DD for deterministic daily variability.")
    parser.add_argument("--steps", type=int, default=240, help="Number of display simulation steps.")
    parser.add_argument("--deep-horizon", type=int, default=10000, help="Deep simulation horizon.")
    parser.add_argument("--pool-size", type=int, default=12, help="Diverse candidate pool size.")
    parser.add_argument("--duration", type=float, default=16.0, help="Animation loop duration in seconds.")
    parser.add_argument("--debug-json", action="store_true", help="Save debug metadata JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files.")

    args = parser.parse_args()

    # Determine date
    target_date = args.date
    if not target_date:
        target_date = datetime.now(DEFAULT_TZ).strftime("%Y-%m-%d")

    if args.input:
        if not args.input.is_file():
            print(f"Error: Input file '{args.input}' does not exist.", file=sys.stderr)
            return 1
        with open(args.input, "r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN environment variable is required when --input is not specified.", file=sys.stderr)
            return 1
        username = args.username or os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not username:
            print("Error: Username must be specified via --username or GITHUB_REPOSITORY_OWNER.", file=sys.stderr)
            return 1
        print(f"Fetching contribution calendar for '{username}' via GitHub GraphQL...")
        payload = fetch_contributions_graphql(token, username)

    light_path, dark_path = generate_all(
        calendar_payload=payload,
        output_dir=args.output_dir,
        date_str=target_date,
        steps_count=args.steps,
        deep_horizon=args.deep_horizon,
        pool_capacity=args.pool_size,
        duration_s=args.duration,
        debug_json=args.debug_json,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        light_size = light_path.stat().st_size
        dark_size = dark_path.stat().st_size
        print("Generated successfully:")
        print(f"  - Light SVG: {light_path} ({light_size:,} bytes)")
        print(f"  - Dark SVG:  {dark_path} ({dark_size:,} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
