#!/usr/bin/env python3
"""CLI tool to fetch GitHub contribution data and generate Langton's Ant SVGs (V2).

Supports both production mode (querying GitHub GraphQL API with GITHUB_TOKEN)
and local/test mode (reading from a JSON fixture file).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.langton_sim import (
    CalendarData,
    SimulationResult,
    parse_contribution_calendar,
    select_best_simulation,
)
from scripts.langton_analysis import DeepAnalysis
from scripts.langton_render import render_langton_svg_v2

API_URL = "https://api.github.com/graphql"

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
            "User-Agent": "leozaow-langton-renderer-v2",
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
    steps_count: int = 240,
    deep_horizon: int = 10000,
    duration_s: float = 16.0,
    debug_json: bool = False,
    dry_run: bool = False,
) -> Tuple[Path, Path]:
    """Runs deep simulation and outputs the V2 light and dark SVGs."""
    calendar = parse_contribution_calendar(calendar_payload)
    simulation, analysis = select_best_simulation(
        calendar,
        steps_count=steps_count,
        deep_horizon=deep_horizon,
    )

    svg_light = render_langton_svg_v2(
        calendar=calendar,
        simulation=simulation,
        analysis=analysis,
        theme="light",
        duration_s=duration_s,
    )
    svg_dark = render_langton_svg_v2(
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

    # Detailed structured logs required by Section 4
    print("=== Langton's Ant V2 Generation Telemetry ===")
    print(f"totalContributions:              {calendar.total_contributions}")
    print(f"activeDays:                      {active_days}")
    print(f"calendarStart:                   {calendar.min_date}")
    print(f"calendarEnd:                     {calendar.max_date}")
    print(f"startPosition:                   W{simulation.start_x:02d}:D{simulation.start_y}")
    print(f"startDirection:                  {simulation.start_dir}")
    print(f"simulationSteps:                 {steps_count}")
    print(f"deepHorizonSimulated:            {analysis.total_simulated}")
    print(f"visibleSteps:                    {visible_in_cal}")
    print(f"uniqueVisited:                   {len(simulation.visited_cells)}")
    print(f"activeContributionCellsVisited:  {analysis.commits_visited}")
    print(f"highwayDetected:                 {analysis.highway_detected}")
    if analysis.highway_detected:
        print(f"highwayPeriod:                   {analysis.highway_period}")
    print("=============================================")

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        light_path.write_text(svg_light, encoding="utf-8")
        dark_path.write_text(svg_dark, encoding="utf-8")

        if debug_json:
            debug_info = {
                "totalContributions": calendar.total_contributions,
                "activeDays": active_days,
                "calendarStart": calendar.min_date,
                "calendarEnd": calendar.max_date,
                "stepsSimulated": analysis.total_simulated,
                "displaySteps": steps_count,
                "start": {
                    "x": simulation.start_x,
                    "y": simulation.start_y,
                    "dir": simulation.start_dir,
                },
                "visibleSteps": visible_in_cal,
                "uniqueVisited": len(simulation.visited_cells),
                "activeContributionCellsVisited": analysis.commits_visited,
                "boundingBox": {
                    "min_x": analysis.bounding_box[0],
                    "max_x": analysis.bounding_box[1],
                    "min_y": analysis.bounding_box[2],
                    "max_y": analysis.bounding_box[3],
                },
                "highwayDetected": analysis.highway_detected,
                "highwayPeriod": analysis.highway_period,
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
    parser = argparse.ArgumentParser(description="Generate Langton's Ant contribution SVGs V2.")
    parser.add_argument("--input", "-i", type=Path, help="Path to input JSON fixture.")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("dist"), help="Directory to save SVGs.")
    parser.add_argument("--username", "-u", type=str, help="GitHub username.")
    parser.add_argument("--steps", type=int, default=240, help="Number of display simulation steps.")
    parser.add_argument("--deep-horizon", type=int, default=10000, help="Deep simulation horizon.")
    parser.add_argument("--duration", type=float, default=16.0, help="Animation loop duration in seconds.")
    parser.add_argument("--debug-json", action="store_true", help="Save debug metadata JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files.")

    args = parser.parse_args()

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
        steps_count=args.steps,
        deep_horizon=args.deep_horizon,
        duration_s=args.duration,
        debug_json=args.debug_json,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        light_size = light_path.stat().st_size
        dark_size = dark_path.stat().st_size
        print(f"Generated successfully:")
        print(f"  - Light SVG: {light_path} ({light_size:,} bytes)")
        print(f"  - Dark SVG:  {dark_path} ({dark_size:,} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
