#!/usr/bin/env python3
"""Generate self-hosted GitHub streak cards for a profile README.

No third-party stats service is required. The workflow uses GitHub GraphQL,
computes the streak locally, and writes light/dark SVGs into assets/.
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


@dataclass
class Stats:
    current_days: int
    longest_days: int
    current_weeks: int
    longest_weeks: int
    total: int
    active_days: int
    last35: list[int]


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
    """Return the Monday of the ISO week containing *d*."""
    return d - timedelta(days=d.weekday())


def _week_has_activity(days: dict[date, int], monday: date) -> bool:
    """Return True if any day Mon-Sun in the given week has contributions."""
    return any(days.get(monday + timedelta(days=i), 0) > 0 for i in range(7))


def compute(days: dict[date, int], today: date) -> Stats:
    if not days:
        return Stats(0, 0, 0, 0, 0, 0, [0] * 35)

    ordered = sorted(days)
    total = sum(days.values())
    active_days = sum(1 for value in days.values() if value > 0)

    # --- Daily streaks ---
    longest_days = 0
    run = 0
    previous: date | None = None
    for d in ordered:
        if previous is not None and d != previous + timedelta(days=1):
            run = 0
        if days[d] > 0:
            run += 1
            longest_days = max(longest_days, run)
        else:
            run = 0
        previous = d

    # Current daily streak: don't punish an unfinished today.
    cursor = today
    if days.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current_days = 0
    while days.get(cursor, 0) > 0:
        current_days += 1
        cursor -= timedelta(days=1)

    # --- Weekly streaks ---
    # A week (Mon-Sun) is active if it has ≥1 contribution.
    # The current (incomplete) week doesn't break the streak if it has no
    # activity yet — we simply don't count it. If it has activity, it counts.
    first_monday = _monday(min(ordered))
    today_monday = _monday(today)

    # Build list of all weeks from first to current.
    week_mondays: list[date] = []
    m = first_monday
    while m <= today_monday:
        week_mondays.append(m)
        m += timedelta(weeks=1)

    # Longest weekly streak (across all history).
    longest_weeks = 0
    run = 0
    for m in week_mondays:
        if _week_has_activity(days, m):
            run += 1
            longest_weeks = max(longest_weeks, run)
        else:
            run = 0

    # Current weekly streak: walk backwards from the most recent active week.
    # If the current week has no activity yet, start from last week.
    start_idx = len(week_mondays) - 1
    if not _week_has_activity(days, week_mondays[start_idx]):
        start_idx -= 1
    current_weeks = 0
    for i in range(start_idx, -1, -1):
        if _week_has_activity(days, week_mondays[i]):
            current_weeks += 1
        else:
            break

    # Last 35 days bar chart.
    start35 = today - timedelta(days=34)
    last35 = [days.get(start35 + timedelta(days=i), 0) for i in range(35)]

    return Stats(current_days, longest_days, current_weeks, longest_weeks, total, active_days, last35)


def render(stats: Stats, username: str, theme: str) -> str:
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    card_bg = "#161b22" if dark else "#f6f8fa"
    border = "#30363d" if dark else "#d0d7de"
    text = "#f0f6fc" if dark else "#1f2328"
    muted = "#8c959f" if dark else "#57606a"
    orange = "#fb8500"
    green = "#3fb950" if dark else "#1a7f37"
    blue = "#58a6ff" if dark else "#0969da"
    purple = "#a371f7" if dark else "#8250df"

    maxv = max(stats.last35) if stats.last35 else 1
    maxv = max(maxv, 1)
    bars = []
    x0, baseline, width, gap = 535, 138, 5, 3
    for i, v in enumerate(stats.last35):
        h = 4 if v == 0 else 8 + int(42 * (v / maxv))
        x = x0 + i * (width + gap)
        y = baseline - h
        opacity = 0.18 if v == 0 else min(1.0, 0.38 + (v / maxv) * 0.62)
        bar_color = orange if i >= (35 - stats.current_days) else green
        bars.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{h}" rx="2.5" fill="{bar_color}" opacity="{opacity:.2f}">'
            f'<animate attributeName="height" from="2" to="{h}" dur="0.55s" begin="{i*0.015:.3f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{baseline-2}" to="{y}" dur="0.55s" begin="{i*0.015:.3f}s" fill="freeze"/>'
            '</rect>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="850" height="205" viewBox="0 0 850 205" role="img" aria-label="Estatísticas e Sequência GitHub de {escape(username)}">
  <defs>
    <linearGradient id="headerLine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{orange}"/>
      <stop offset="30%" stop-color="#ffb703"/>
      <stop offset="70%" stop-color="{blue}"/>
      <stop offset="100%" stop-color="{green}"/>
    </linearGradient>
    <filter id="ringGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <style>
      .badge-title {{ font: 700 12px ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: 1.5px; fill: {muted}; }}
      .stat-num {{ font: 800 32px 'Segoe UI', Ubuntu, -apple-system, sans-serif; fill: {text}; }}
      .stat-num-orange {{ font: 800 34px 'Segoe UI', Ubuntu, -apple-system, sans-serif; fill: {orange}; }}
      .stat-label {{ font: 700 11px ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing: 0.8px; fill: {muted}; }}
      .flame {{ animation: pulseFlame 2s ease-in-out infinite; transform-origin: 72px 14px; }}
      @keyframes pulseFlame {{ 0%, 100% {{ transform: scale(1); }} 50% {{ transform: scale(1.15); }} }}
    </style>
  </defs>

  <!-- Card Background -->
  <rect x="1" y="1" width="848" height="203" rx="16" fill="{bg}" stroke="{border}"/>
  <rect x="1" y="1" width="848" height="4" rx="2" fill="url(#headerLine)"/>

  <!-- Card Title -->
  <text x="28" y="32" class="badge-title">GITHUB STATS &amp; STREAK</text>
  <text x="822" y="32" text-anchor="end" class="stat-sub">TZ: America/Sao_Paulo</text>

  <!-- Column 1: Total Contributions -->
  <g transform="translate(28, 48)">
    <rect width="180" height="135" rx="12" fill="{card_bg}" stroke="{border}" stroke-width="0.8"/>
    <!-- Icon: Chart icon -->
    <path d="M 20 38 L 20 22 M 28 38 L 28 14 M 36 38 L 36 30" stroke="{blue}" stroke-width="2.5" stroke-linecap="round"/>
    <text x="50" y="32" class="stat-label">TOTAL</text>
    <text x="20" y="80" class="stat-num">{stats.total:,}</text>
    <text x="20" y="104" class="stat-sub">CONTRIBUIÇÕES</text>
    <text x="20" y="122" class="stat-sub" fill="{green}">{stats.active_days} dias com atividade</text>
  </g>

    <!-- Column 2: Current Streak (Highlighted Centerpiece) -->
  <g transform="translate(222, 48)">
    <rect width="270" height="135" rx="12" fill="{card_bg}" stroke="{orange}" stroke-width="1.2" opacity="0.95"/>
    
    <!-- Circular Flame Badge (Centered at cx=68, cy=67, r=42) -->
    <circle cx="68" cy="67" r="42" fill="none" stroke="{border}" stroke-width="4"/>
    <circle cx="68" cy="67" r="42" fill="none" stroke="{orange}" stroke-width="4" stroke-dasharray="264" stroke-dashoffset="66" stroke-linecap="round" filter="url(#ringGlow)"/>
    
    <!-- Clean Crisp Flame Icon at top of ring -->
    <path d="M 68 36 C 68 36 74 44 74 49 C 74 52 71.5 55 68 55 C 64.5 55 62 52 62 49 C 62 44 68 36 68 36 Z" fill="{orange}"/>
    
    <!-- Number and label inside ring -->
    <text x="68" y="80" text-anchor="middle" class="stat-num-orange">{stats.current_days}</text>
    <text x="68" y="96" text-anchor="middle" class="stat-sub">DIAS</text>

    <!-- Info beside ring -->
    <text x="126" y="38" class="stat-label" fill="{orange}">SEQUÊNCIA ATUAL</text>
    <text x="126" y="66" class="stat-num" style="font-size: 24px;">{stats.current_weeks} <tspan font-size="13" font-weight="500" fill="{muted}">semanas</tspan></text>
    <text x="126" y="86" class="stat-sub">consecutivas ativas</text>
    <line x1="126" y1="98" x2="252" y2="98" stroke="{border}" stroke-width="1"/>
    <text x="126" y="118" class="stat-sub">Recorde: <tspan font-weight="700" fill="{text}">{stats.longest_days} dias</tspan></text>
  </g>

  <!-- Column 3: Recent Activity (Last 35 Days Chart + Record Info) -->
  <g transform="translate(506, 48)">
    <rect width="316" height="135" rx="12" fill="{card_bg}" stroke="{border}" stroke-width="0.8"/>
    <text x="18" y="28" class="stat-label">ÚLTIMOS 35 DIAS</text>
    <text x="298" y="28" text-anchor="end" class="stat-sub">Recorde: {stats.longest_weeks} sem.</text>
  </g>

  <!-- Bars inside Column 3 -->
  {''.join(bars)}
  <text x="804" y="166" text-anchor="end" class="stat-sub">Atualização automática</text>
</svg>'''


def demo_days(today: date) -> dict[date, int]:
    out = {}
    for i in range(540):
        d = today - timedelta(days=539 - i)
        # deterministic pseudo-pattern for local preview only
        v = ((i * 7 + i // 9) % 11)
        out[d] = 0 if v < 4 else (v - 3)
    # force a visible current streak
    for i in range(12):
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
