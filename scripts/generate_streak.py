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
    current: int
    longest: int
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


def compute(days: dict[date, int], today: date) -> Stats:
    if not days:
        return Stats(0, 0, 0, 0, [0] * 35)

    ordered = sorted(days)
    total = sum(days.values())
    active_days = sum(1 for value in days.values() if value > 0)

    longest = 0
    run = 0
    previous: date | None = None
    for d in ordered:
        if previous is not None and d != previous + timedelta(days=1):
            run = 0
        if days[d] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        previous = d

    # Do not punish an unfinished current day. If today is still empty,
    # calculate the live streak from yesterday.
    cursor = today
    if days.get(cursor, 0) == 0:
        cursor -= timedelta(days=1)
    current = 0
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    start35 = today - timedelta(days=34)
    last35 = [days.get(start35 + timedelta(days=i), 0) for i in range(35)]
    return Stats(current, longest, total, active_days, last35)


def render(stats: Stats, username: str, theme: str) -> str:
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    panel = "#161b22" if dark else "#f6f8fa"
    border = "#30363d" if dark else "#d0d7de"
    text = "#f0f6fc" if dark else "#1f2328"
    muted = "#8c959f" if dark else "#57606a"
    green = "#3fb950" if dark else "#1a7f37"
    blue = "#58a6ff" if dark else "#0969da"
    purple = "#a371f7" if dark else "#8250df"

    maxv = max(stats.last35) if stats.last35 else 1
    maxv = max(maxv, 1)
    bars = []
    x0, baseline, width, gap = 525, 140, 5, 3
    for i, v in enumerate(stats.last35):
        h = 4 if v == 0 else 8 + int(48 * (v / maxv))
        x = x0 + i * (width + gap)
        y = baseline - h
        opacity = 0.18 if v == 0 else min(1.0, 0.38 + (v / maxv) * 0.62)
        bars.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{h}" rx="3" fill="{green}" opacity="{opacity:.2f}">' \
            f'<animate attributeName="height" from="2" to="{h}" dur="0.55s" begin="{i*0.015:.3f}s" fill="freeze"/>' \
            f'<animate attributeName="y" from="{baseline-2}" to="{y}" dur="0.55s" begin="{i*0.015:.3f}s" fill="freeze"/>' \
            '</rect>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="846" height="190" viewBox="0 0 846 190" role="img" aria-label="GitHub build streak for {escape(username)}">
  <defs>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{blue}"/><stop offset="0.5" stop-color="{purple}"/><stop offset="1" stop-color="{green}"/>
    </linearGradient>
    <style>
      .title{{font:700 13px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:1.5px;fill:{muted}}}
      .big{{font:700 34px 'Segoe UI',Ubuntu,sans-serif;fill:{text}}}
      .label{{font:600 11px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.7px;fill:{muted}}}
      .small{{font:600 11px ui-monospace,SFMono-Regular,Consolas,monospace;fill:{muted}}}
    </style>
  </defs>
  <rect x="1" y="1" width="844" height="188" rx="16" fill="{bg}" stroke="{border}"/>
  <rect x="18" y="18" width="810" height="3" rx="2" fill="url(#line)" opacity=".85"/>
  <text x="28" y="48" class="title">BUILD STREAK // SELF-HOSTED</text>

  <g transform="translate(28,68)">
    <text x="0" y="32" class="big">{stats.current}</text>
    <text x="0" y="55" class="label">CURRENT DAYS</text>
  </g>
  <g transform="translate(190,68)">
    <text x="0" y="32" class="big">{stats.longest}</text>
    <text x="0" y="55" class="label">LONGEST STREAK</text>
  </g>
  <g transform="translate(370,68)">
    <text x="0" y="32" class="big">{stats.total:,}</text>
    <text x="0" y="55" class="label">CONTRIBUTIONS</text>
  </g>

  <text x="525" y="71" class="label">LAST 35 DAYS</text>
  {''.join(bars)}
  <text x="525" y="164" class="small">GitHub data · America/Sao_Paulo</text>
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
    print(f"current={stats.current} longest={stats.longest} total={stats.total} active_days={stats.active_days}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
