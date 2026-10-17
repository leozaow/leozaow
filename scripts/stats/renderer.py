"""Accessible, responsive SVG renderer for GitHub contribution streak analytics."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Optional

from scripts.stats.models import StreakStats

FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "card_bg": "#161b22",
        "border": "#30363d",
        "divider": "#21262d",
        "text_primary": "#f0f6fc",
        "text_secondary": "#8c959f",
        "text_muted": "#6e7681",
        "accent_streak": "#fb8c00",
        "accent_streak_glow": "rgba(251, 140, 0, 0.4)",
        "accent_longest": "#58a6ff",
        "accent_contributions": "#3fb950",
        "bar_default": "#3fb950",
        "bar_streak": "#fb8c00",
        "bar_inactive": "#21262d",
        "badge_bg": "rgba(56, 139, 253, 0.15)",
        "flame_ring": "#fb8c00",
    },
    "light": {
        "bg": "#ffffff",
        "card_bg": "#f6f8fa",
        "border": "#d0d7de",
        "divider": "#eaeef2",
        "text_primary": "#1f2328",
        "text_secondary": "#57606a",
        "text_muted": "#8c959f",
        "accent_streak": "#d97706",
        "accent_streak_glow": "rgba(217, 119, 6, 0.35)",
        "accent_longest": "#0969da",
        "accent_contributions": "#1a7f37",
        "bar_default": "#1a7f37",
        "bar_streak": "#d97706",
        "bar_inactive": "#eaeef2",
        "badge_bg": "rgba(9, 105, 218, 0.1)",
        "flame_ring": "#d97706",
    },
}


def format_date_range(start: Optional[date], end: Optional[date]) -> str:
    """Formats a date range concisely and unambiguously."""
    if not start or not end:
        return "No active streak"
    if start == end:
        return start.strftime("%b %d, %Y")
    if start.year == end.year:
        return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}"


def render_streak_svg(stats: StreakStats, theme: str = "dark") -> str:
    """Renders a self-contained, accessible, animated SVG card representing streak statistics."""
    palette = THEMES.get(theme, THEMES["dark"])

    username = escape(stats.username)
    curr_streak_days = stats.current_streak.length
    longest_streak_days = stats.longest_streak.length
    total_year = stats.contributions_last_year
    active_year = stats.active_days_last_year

    curr_range = format_date_range(stats.current_streak.start_date, stats.current_streak.end_date)
    longest_range = format_date_range(stats.longest_streak.start_date, stats.longest_streak.end_date)

    pct_active = int(round((active_year / 365.0) * 100)) if total_year > 0 else 0

    # 35-day activity chart geometry
    chart_bars = stats.recent_activity
    max_count = max((bar.count for bar in chart_bars), default=1)
    max_count = max(max_count, 1)

    chart_x0 = 620.0
    chart_y_base = 138.0
    bar_w = 4.0
    bar_gap = 2.4
    max_bar_h = 56.0

    rendered_bars = []
    for idx, bar in enumerate(chart_bars):
        x = chart_x0 + idx * (bar_w + bar_gap)
        if bar.count == 0:
            h = 3.5
            y = chart_y_base - h
            fill_color = palette["bar_inactive"]
            opacity = 0.5
        else:
            h = max(7.0, (bar.count / max_count) * max_bar_h)
            y = chart_y_base - h
            fill_color = palette["bar_streak"] if bar.is_current_streak else palette["bar_default"]
            opacity = min(1.0, 0.45 + (bar.count / max_count) * 0.55)

        rendered_bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" rx="1.5" '
            f'fill="{fill_color}" opacity="{opacity:.2f}">'
            f'<title>{bar.date.strftime("%b %d, %Y")}: {bar.count} contributions</title>'
            f'</rect>'
        )

    bars_svg = "\n      ".join(rendered_bars)

    # Date axis labels for the chart
    earliest_chart_date = chart_bars[0].date.strftime("%b %d") if chart_bars else "34d ago"
    latest_chart_date = "Today"

    # Flame icon path
    flame_path = (
        "M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 "
        "C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 "
        "C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z "
        "M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 "
        "C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 "
        "C 4.51 16.85 2.36 19 -0.29 19 Z"
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 195" width="850" height="195" role="img" aria-label="GitHub Streak Analytics for {username}">
  <title>GitHub Contribution Streak Analytics — {username}</title>
  <desc>Current streak: {curr_streak_days} days ({curr_range}). Longest streak: {longest_streak_days} days ({longest_range}). Contributions in the last 365 days: {total_year:,} across {active_year} active days.</desc>

  <defs>
    <style>
      .txt-val {{ font-family: {FONT_STACK}; font-size: 28px; font-weight: 700; fill: {palette['text_primary']}; }}
      .txt-lbl {{ font-family: {FONT_STACK}; font-size: 11px; font-weight: 600; fill: {palette['text_secondary']}; letter-spacing: 0.5px; text-transform: uppercase; }}
      .txt-sub {{ font-family: {FONT_STACK}; font-size: 11px; font-weight: 400; fill: {palette['text_muted']}; }}
      .txt-accent {{ fill: {palette['accent_streak']}; font-weight: 600; }}
      .txt-chart {{ font-family: {FONT_STACK}; font-size: 10px; font-weight: 400; fill: {palette['text_muted']}; }}
      .flame-pulse {{
        transform-box: fill-box;
        transform-origin: center;
        animation: flamePulse 2.4s ease-in-out infinite;
      }}
      @keyframes flamePulse {{
        0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 2px {palette['accent_streak_glow']}); }}
        50% {{ transform: scale(1.08); filter: drop-shadow(0 0 6px {palette['accent_streak_glow']}); }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .flame-pulse {{ animation: none !important; }}
      }}
    </style>
    <filter id="flameGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <mask id="ringGap">
      <rect width="850" height="195" fill="white"/>
      <ellipse cx="308" cy="34" rx="13" ry="15" fill="black"/>
    </mask>
  </defs>

  <!-- Background Base Card -->
  <rect x="0.5" y="0.5" width="849" height="194" rx="10" fill="{palette['bg']}" stroke="{palette['border']}"/>

  <!-- Vertical Zone Dividers -->
  <line x1="195" y1="24" x2="195" y2="170" stroke="{palette['divider']}" stroke-width="1"/>
  <line x1="422" y1="24" x2="422" y2="170" stroke="{palette['divider']}" stroke-width="1"/>
  <line x1="605" y1="24" x2="605" y2="170" stroke="{palette['divider']}" stroke-width="1"/>

  <!-- ZONE 1: Total Contributions (Last 365 Days) -->
  <g transform="translate(97, 0)">
    <text x="0" y="75" text-anchor="middle" class="txt-val">{total_year:,}</text>
    <text x="0" y="105" text-anchor="middle" class="txt-lbl">LAST 365 DAYS</text>
    <text x="0" y="130" text-anchor="middle" class="txt-sub">GitHub Contributions</text>
    <text x="0" y="150" text-anchor="middle" class="txt-sub">{active_year} active days ({pct_active}%)</text>
  </g>

  <!-- ZONE 2: Current Streak (Centerpiece with Ring & Flame) -->
  <g>
    <!-- Halo Ring with Gap -->
    <circle cx="308" cy="70" r="39" fill="none" stroke="{palette['flame_ring']}" stroke-width="4.5" mask="url(#ringGap)"/>

    <!-- Flame Glyph at Crown -->
    <g transform="translate(308, 20)" class="flame-pulse" filter="url(#flameGlow)">
      <path d="{flame_path}" fill="{palette['accent_streak']}"/>
    </g>

    <!-- Streak Count Inside Ring -->
    <text x="308" y="79" text-anchor="middle" class="txt-val">{curr_streak_days}</text>

    <!-- Current Streak Labels -->
    <text x="308" y="128" text-anchor="middle" class="txt-lbl txt-accent">CURRENT STREAK</text>
    <text x="308" y="148" text-anchor="middle" class="txt-sub">{curr_range}</text>
  </g>

  <!-- ZONE 3: Longest Streak -->
  <g transform="translate(513, 0)">
    <text x="0" y="75" text-anchor="middle" class="txt-val">{longest_streak_days}</text>
    <text x="0" y="105" text-anchor="middle" class="txt-lbl">LONGEST STREAK</text>
    <text x="0" y="130" text-anchor="middle" class="txt-sub">{longest_range}</text>
    <text x="0" y="150" text-anchor="middle" class="txt-sub">All-time record streak</text>
  </g>

  <!-- ZONE 4: Recent 35 Days Activity Chart -->
  <g>
    <text x="620" y="44" class="txt-lbl">RECENT ACTIVITY</text>
    <text x="830" y="44" text-anchor="end" class="txt-sub">35 days</text>

    <!-- Contribution Bars -->
    <g>
      {bars_svg}
    </g>

    <!-- Chart Axis Labels -->
    <text x="620" y="158" class="txt-chart">{earliest_chart_date}</text>
    <text x="830" y="158" text-anchor="end" class="txt-chart">{latest_chart_date}</text>
  </g>
</svg>"""

    return svg
