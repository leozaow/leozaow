#!/usr/bin/env python3
"""Generate self-hosted GitHub streak cards for a profile README.

Self-hosted generator matching the iconic github-readme-streak-stats design,
computing streaks locally from GitHub GraphQL API, rendered into assets/.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://api.github.com/graphql"
TZ = ZoneInfo("America/Sao_Paulo")

PT_MONTHS = ["Jan.", "Fev.", "Mar.", "Abr.", "Mai.", "Jun.", "Jul.", "Ago.", "Set.", "Out.", "Nov.", "Dez."]


@dataclass
class Stats:
    current_days: int
    longest_days: int
    current_weeks: int
    longest_weeks: int
    total: int
    active_days: int
    start_date: date | None = None
    current_start: date | None = None
    current_end: date | None = None
    longest_start: date | None = None
    longest_end: date | None = None


def fmt_date_year(d: date | None) -> str:
    if not d:
        return "Presente"
    return f"{PT_MONTHS[d.month - 1]} {d.year}"


def gql(token: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "leozaow-profile-streak",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
    return payload["data"]


def fetch_created_at(token: str, username: str) -> date:
    query = """
    query($login: String!) {
      user(login: $login) { createdAt }
    }
    """
    data = gql(token, query, {"login": username})
    if not data.get("user"):
        raise RuntimeError(f"GitHub user not found: {username}")
    return datetime.fromisoformat(data["user"]["createdAt"].replace("Z", "+00:00")).date()


def fetch_days(token: str, username: str, start: date, end: date) -> dict[date, int]:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
      }
    }
    """
    out: dict[date, int] = {}
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=364), end)
        from_dt = datetime.combine(cursor, datetime.min.time(), tzinfo=timezone.utc)
        to_dt = datetime.combine(chunk_end, datetime.max.time(), tzinfo=timezone.utc)
        data = gql(
            token,
            query,
            {
                "login": username,
                "from": from_dt.isoformat().replace("+00:00", "Z"),
                "to": to_dt.isoformat().replace("+00:00", "Z"),
            },
        )
        weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for day in week["contributionDays"]:
                d = date.fromisoformat(day["date"])
                if start <= d <= end:
                    out[d] = int(day["contributionCount"])
        cursor = chunk_end + timedelta(days=1)
    return out


def _monday(d: date) -> date:
    """Return the Monday of the ISO week containing d."""
    return d - timedelta(days=d.weekday())


def _week_has_activity(days: dict[date, int], monday: date) -> bool:
    """Return True if any day Mon-Sun in the given week has contributions."""
    return any(days.get(monday + timedelta(days=i), 0) > 0 for i in range(7))


def compute(days: dict[date, int], today: date) -> Stats:
    if not days:
        return Stats(0, 0, 0, 0, 0, 0)

    ordered = sorted(days)
    start_date = ordered[0] if ordered else None
    total = sum(days.values())
    active_days = sum(1 for value in days.values() if value > 0)

    # --- Daily streaks ---
    longest_days = 0
    run = 0
    run_start: date | None = None
    longest_start: date | None = None
    longest_end: date | None = None
    previous: date | None = None

    for d in ordered:
        if previous is not None and d != previous + timedelta(days=1):
            run = 0
            run_start = None
        if days[d] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run > longest_days:
                longest_days = run
                longest_start = run_start
                longest_end = d
        else:
            run = 0
            run_start = None
        previous = d

    # Current daily streak: don't punish an unfinished today.
    cursor = today
    if days.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current_end = cursor
    current_days = 0
    while days.get(cursor, 0) > 0:
        current_days += 1
        cursor -= timedelta(days=1)
    current_start = cursor + timedelta(days=1) if current_days > 0 else today

    # --- Weekly streaks ---
    first_monday = _monday(min(ordered))
    today_monday = _monday(today)

    week_mondays: list[date] = []
    m = first_monday
    while m <= today_monday:
        week_mondays.append(m)
        m += timedelta(weeks=1)

    longest_weeks = 0
    run = 0
    for m in week_mondays:
        if _week_has_activity(days, m):
            run += 1
            longest_weeks = max(longest_weeks, run)
        else:
            run = 0

    start_idx = len(week_mondays) - 1
    if not _week_has_activity(days, week_mondays[start_idx]):
        start_idx -= 1
    current_weeks = 0
    for i in range(start_idx, -1, -1):
        if _week_has_activity(days, week_mondays[i]):
            current_weeks += 1
        else:
            break

    return Stats(
        current_days=current_days,
        longest_days=longest_days,
        current_weeks=current_weeks,
        longest_weeks=longest_weeks,
        total=total,
        active_days=active_days,
        start_date=start_date,
        current_start=current_start,
        current_end=current_end,
        longest_start=longest_start,
        longest_end=longest_end,
    )


def render(stats: Stats, username: str, theme: str) -> str:
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    text = "#f0f6fc" if dark else "#1f2328"
    muted = "#8c959f" if dark else "#57606a"
    orange = "#fb8c00"

    total_range = f"{fmt_date_year(stats.start_date)} – Presente" if stats.start_date else "Presente"
    current_weeks_label = f"{stats.current_weeks} semanas consecutivas"
    longest_weeks_label = f"Recorde: {stats.longest_weeks} semanas"

    font_stack = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, 'Helvetica Neue', Helvetica, Arial, sans-serif"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     style="isolation: isolate;" viewBox="0 0 495 195" width="495px" height="195px" direction="ltr" role="img" aria-label="Estatísticas e Sequência GitHub de {escape(username)}">
  <defs>
    <style>
      @keyframes currstreak {{
        0% {{ font-size: 3px; opacity: 0.2; }}
        80% {{ font-size: 34px; opacity: 1; }}
        100% {{ font-size: 28px; opacity: 1; }}
      }}
      @keyframes fadein {{
        0% {{ opacity: 0; }}
        100% {{ opacity: 1; }}
      }}
      @keyframes flamePulse {{
        0%, 100% {{
          transform: scale(1);
          filter: drop-shadow(0 0 2px rgba(251, 140, 0, 0.45));
        }}
        50% {{
          transform: scale(1.08);
          filter: drop-shadow(0 0 7px rgba(251, 140, 0, 0.9));
        }}
      }}
    </style>
    <clipPath id="outer_rectangle">
      <rect width="495" height="195" rx="8"/>
    </clipPath>
    <mask id="mask_out_ring_behind_fire">
      <rect width="495" height="195" fill="white"/>
      <ellipse id="mask-ellipse" cx="247.5" cy="32" rx="14" ry="18" fill="black"/>
    </mask>
  </defs>

  <g clip-path="url(#outer_rectangle)">
    <!-- Background Card -->
    <rect stroke="{border}" fill="{bg}" rx="8" x="0.5" y="0.5" width="494" height="194"/>

    <!-- Clean Vertical Dividers -->
    <line x1="165" y1="28" x2="165" y2="170" stroke="{border}" stroke-width="1"/>
    <line x1="330" y1="28" x2="330" y2="170" stroke="{border}" stroke-width="1"/>

    <!-- Column 1: Total Contributions -->
    <g style="isolation: isolate;">
      <g transform="translate(82.5, 48)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.5s;">
          {stats.total:,}
        </text>
      </g>
      <g transform="translate(82.5, 84)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="600" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s;">
          Total de Contribuições
        </text>
      </g>
      <g transform="translate(82.5, 114)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s;">
          {total_range}
        </text>
      </g>
    </g>

    <!-- Column 2: Current Streak (Centerpiece) -->
    <g style="isolation: isolate;">
      <!-- Streak Ring with Masked Gap -->
      <g mask="url(#mask_out_ring_behind_fire)">
        <circle cx="247.5" cy="71" r="40" fill="none" stroke="{orange}" stroke-width="5" style="opacity: 0; animation: fadein 0.5s linear forwards 0.3s;"/>
      </g>

      <!-- Animated Fire Icon with Pulsing Flame Effect -->
      <g transform="translate(247.5, 19.5)" style="transform-origin: 247.5px 33px; animation: flamePulse 2.2s ease-in-out infinite, fadein 0.5s linear forwards 0.5s;">
        <path d="M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z" fill="none"/>
        <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="{orange}"/>
      </g>

      <!-- Current Streak Big Number -->
      <g transform="translate(247.5, 48)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="animation: currstreak 0.6s linear forwards;">
          {stats.current_days}
        </text>
      </g>

      <!-- Current Streak Label -->
      <g transform="translate(247.5, 108)">
        <text x="0" y="32" text-anchor="middle" fill="{orange}" font-family="{font_stack}" font-weight="700" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s;">
          Sequência Atual
        </text>
      </g>

      <!-- Current Streak Range & Weeks -->
      <g transform="translate(247.5, 145)">
        <text x="0" y="21" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s;">
          {current_weeks_label}
        </text>
      </g>
    </g>

    <!-- Column 3: Longest Streak -->
    <g style="isolation: isolate;">
      <g transform="translate(412.5, 48)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s;">
          {stats.longest_days}
        </text>
      </g>
      <g transform="translate(412.5, 84)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="600" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s;">
          Maior Sequência
        </text>
      </g>
      <g transform="translate(412.5, 114)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s;">
          {longest_weeks_label}
        </text>
      </g>
    </g>
  </g>
</svg>'''


def demo_days(today: date) -> dict[date, int]:
    out = {}
    for i in range(540):
        d = today - timedelta(days=539 - i)
        v = ((i * 7 + i // 9) % 11)
        out[d] = 0 if v < 4 else (v - 3)
    for i in range(4):
        out[today - timedelta(days=i)] = 1 + (i % 5)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    outdir = root / "assets"
    outdir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(TZ).date()

    if "--demo" in sys.argv:
        username = "leozaow"
        days = demo_days(today)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        username = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_USER") or "leozaow"
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required")
        created = fetch_created_at(token, username)
        days = fetch_days(token, username, created, today)

    stats = compute(days, today)
    for theme in ("light", "dark"):
        (outdir / f"streak.{theme}.svg").write_text(render(stats, username, theme), encoding="utf-8")
    print(
        f"current_days={stats.current_days} longest_days={stats.longest_days} "
        f"current_weeks={stats.current_weeks} longest_weeks={stats.longest_weeks} "
        f"total={stats.total} active_days={stats.active_days}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
