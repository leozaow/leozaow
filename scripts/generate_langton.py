#!/usr/bin/env python3
"""CLI tool to fetch GitHub contribution data and generate Langton's Ant SVGs.

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
from scripts.langton_render import render_langton_svg

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
            "User-Agent": "leozaow-langton-renderer",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    if payload.get("errors"):
        # Ensure token is never leaked in error messages
        err_msg = json.dumps(payload["errors"], ensure_ascii=False)
        raise RuntimeError(f"GitHub GraphQL error: {err_msg}")

    user_data = payload.get("data", {}).get("user")
    if not user_data:
        raise ValueError(f"GitHub user '{username}' not found or no data returned.")

    return payload


def generate_all(
    calendar_payload: dict,
    output_dir: Path,
    steps_count: int = 180,
    duration_s: float = 14.0,
    debug_json: bool = False,
    dry_run: bool = False,
) -> Tuple[Path, Path]:
    """Runs the simulation and outputs the light and dark SVGs."""
    calendar = parse_contribution_calendar(calendar_payload)
    simulation = select_best_simulation(calendar, steps_count=steps_count)

    svg_light = render_langton_svg(calendar, simulation, theme="light", duration_s=duration_s)
    svg_dark = render_langton_svg(calendar, simulation, theme="dark", duration_s=duration_s)

    light_path = output_dir / "langton-contribution-graph.svg"
    dark_path = output_dir / "langton-contribution-graph-dark.svg"

    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        light_path.write_text(svg_light, encoding="utf-8")
        dark_path.write_text(svg_dark, encoding="utf-8")

        if debug_json:
            debug_info = {
                "totalContributions": calendar.total_contributions,
                "weeksCount": calendar.weeks_count,
                "start": {"x": simulation.start_x, "y": simulation.start_y, "dir": simulation.start_dir},
                "steps": len(simulation.steps),
                "uniqueVisited": len(simulation.visited_cells),
                "highwayDetected": simulation.highway_detected,
                "highwayPeriod": simulation.highway_period,
            }
            (output_dir / "langton-debug.json").write_text(json.dumps(debug_info, indent=2), encoding="utf-8")

    return light_path, dark_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Langton's Ant contribution SVGs.")
    parser.add_argument("--input", "-i", type=Path, help="Path to input JSON fixture.")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("dist"), help="Directory to save SVGs.")
    parser.add_argument("--username", "-u", type=str, help="GitHub username.")
    parser.add_argument("--steps", type=int, default=180, help="Number of simulation steps.")
    parser.add_argument("--duration", type=float, default=14.0, help="Animation loop duration in seconds.")
    parser.add_argument("--debug-json", action="store_true", help="Save debug metadata JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing files.")

    args = parser.parse_args()

    # Determine input source
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
