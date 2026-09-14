#!/usr/bin/env python3
"""Generate self-hosted GitHub streak cards for a profile README.

Self-hosted generator combining the iconic streak-stats card aesthetics
with the 35-day contribution activity bar chart, computed locally via GitHub GraphQL.
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
    last35: list[int]
    start_date: date | None = None
    current_start: date | None = None
    current_end: date | None = None
    longest_start: date | None = None
    longest_end: date | None = None


def fmt_date(d: date | None) -> str:
    if not d:
        return ""
    return f"{d.day} {PT_MONTHS[d.month - 1].lower()}"


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
        return Stats(0, 0, 0, 0, 0, 0, [0] * 35)

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

    # Last 35 days activity
    start35 = today - timedelta(days=34)
    last35 = [days.get(start35 + timedelta(days=i), 0) for i in range(35)]

    return Stats(
        current_days=current_days,
        longest_days=longest_days,
        current_weeks=current_weeks,
        longest_weeks=longest_weeks,
        total=total,
        active_days=active_days,
        last35=last35,
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
    green = "#3fb950" if dark else "#1a7f37"

    total_range = f"{fmt_date_year(stats.start_date)} – Presente" if stats.start_date else "Presente"
    current_weeks_label = f"{stats.current_weeks} semanas consecutivas"
    longest_weeks_label = f"Recorde: {stats.longest_weeks} semanas"

    if stats.longest_start and stats.longest_end:
        longest_dates = f"{fmt_date(stats.longest_start)} – {fmt_date(stats.longest_end)}"
    else:
        longest_dates = ""

    font_stack = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, 'Helvetica Neue', Helvetica, Arial, sans-serif"

    # Build 35 days bars
    maxv = max(stats.last35) if stats.last35 else 1
    maxv = max(maxv, 1)
    bars = []
    x0, baseline, width, gap = 625, 138, 4, 2
    for i, v in enumerate(stats.last35):
        h = 4 if v == 0 else 8 + int(50 * (v / maxv))
        x = x0 + i * (width + gap)
        y = baseline - h
        opacity = 0.22 if v == 0 else min(1.0, 0.45 + (v / maxv) * 0.55)
        # Highlight days belonging to the current streak
        bar_color = orange if (stats.current_days > 0 and i >= (35 - stats.current_days)) else green
        bars.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{h}" rx="2" fill="{bar_color}" opacity="{opacity:.2f}">'
            f'<animate attributeName="height" from="2" to="{h}" dur="0.55s" begin="{i*0.012:.3f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{baseline-2}" to="{y}" dur="0.55s" begin="{i*0.012:.3f}s" fill="freeze"/>'
            '</rect>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     style="isolation: isolate;" viewBox="0 0 850 195" width="850px" height="195px" direction="ltr" role="img" aria-label="Estatísticas e Sequência GitHub de {escape(username)}">
  <defs>
    <style>
      @keyframes currstreak {{
        0% {{ font-size: 4px; opacity: 0.2; }}
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
          filter: drop-shadow(0 0 2px rgba(251, 140, 0, 0.5));
        }}
        50% {{
          transform: scale(1.1);
          filter: drop-shadow(0 0 8px rgba(251, 140, 0, 0.95));
        }}
      }}
      .flame-elem {{
        transform-box: fill-box;
        transform-origin: center;
        animation: flamePulse 2.2s ease-in-out infinite;
      }}
    </style>
    <clipPath id="outer_rectangle">
      <rect width="850" height="195" rx="10"/>
    </clipPath>
    <mask id="mask_ring_flame">
      <rect width="850" height="195" fill="white"/>
      <ellipse cx="312" cy="33" rx="14" ry="16" fill="black"/>
    </mask>
    <filter id="flameGlow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="glow"/>
      <feMerge>
        <feMergeNode in="glow"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <g clip-path="url(#outer_rectangle)">
    <!-- Main Background Card -->
    <rect stroke="{border}" fill="{bg}" rx="10" x="0.5" y="0.5" width="849" height="194"/>

    <!-- 3 Subtle Vertical Dividers -->
    <line x1="195" y1="26" x2="195" y2="168" stroke="{border}" stroke-width="1"/>
    <line x1="430" y1="26" x2="430" y2="168" stroke="{border}" stroke-width="1"/>
    <line x1="605" y1="26" x2="605" y2="168" stroke="{border}" stroke-width="1"/>

    <!-- ZONE 1: Total Contributions -->
    <g style="isolation: isolate;">
      <g transform="translate(97, 48)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.4s;">
          {stats.total:,}
        </text>
      </g>
      <g transform="translate(97, 84)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="600" font-size="13px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.5s;">
          Total de Contribuições
        </text>
      </g>
      <g transform="translate(97, 114)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s;">
          {total_range}
        </text>
      </g>
      <g transform="translate(97, 134)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="11px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s;">
          {stats.active_days} dias com atividade
        </text>
      </g>
    </g>

    <!-- ZONE 2: Current Streak (Centerpiece with Ring & Glowing Flame) -->
    <g style="isolation: isolate;">
      <!-- Ring with gap for flame -->
      <g mask="url(#mask_ring_flame)">
        <circle cx="312" cy="72" r="40" fill="none" stroke="{orange}" stroke-width="5" style="opacity: 0; animation: fadein 0.5s linear forwards 0.3s;"/>
      </g>

      <!-- Authentic Flame Icon: perfectly seated at the crown of the ring -->
      <g transform="translate(312, 20.5)" filter="url(#flameGlow)" class="flame-elem">
        <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="{orange}"/>
      </g>

      <!-- Big Number Inside Ring -->
      <g transform="translate(312, 49)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="animation: currstreak 0.6s linear forwards;">
          {stats.current_days}
        </text>
      </g>

      <!-- Label under ring -->
      <g transform="translate(312, 108)">
        <text x="0" y="32" text-anchor="middle" fill="{orange}" font-family="{font_stack}" font-weight="700" font-size="14px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s;">
          Sequência Atual
        </text>
      </g>

      <!-- Weekly streak detail -->
      <g transform="translate(312, 134)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="500" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s;">
          {current_weeks_label}
        </text>
      </g>
    </g>

    <!-- ZONE 3: Longest Streak -->
    <g style="isolation: isolate;">
      <g transform="translate(517, 48)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="700" font-size="28px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s;">
          {stats.longest_days}
        </text>
      </g>
      <g transform="translate(517, 84)">
        <text x="0" y="32" text-anchor="middle" fill="{text}" font-family="{font_stack}" font-weight="600" font-size="13px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s;">
          Maior Sequência
        </text>
      </g>
      <g transform="translate(517, 114)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="12px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s;">
          {longest_weeks_label}
        </text>
      </g>
      <g transform="translate(517, 134)">
        <text x="0" y="32" text-anchor="middle" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="11px" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s;">
          {longest_dates}
        </text>
      </g>
    </g>

    <!-- ZONE 4: Recent 35 Days Activity Chart -->
    <g style="isolation: isolate;">
      <text x="625" y="44" fill="{text}" font-family="{font_stack}" font-weight="600" font-size="12px" letter-spacing="0.5px">ÚLTIMOS 35 DIAS</text>
      <text x="830" y="44" text-anchor="end" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="11px">Atividade diária</text>

      <!-- Contribution bars -->
      {''.join(bars)}

      <!-- Bar chart labels -->
      <text x="625" y="158" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="10px">35 dias atrás</text>
      <text x="830" y="158" text-anchor="end" fill="{muted}" font-family="{font_stack}" font-weight="400" font-size="10px">Hoje</text>
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
