#!/usr/bin/env python3
"""SVG renderer for Langton's Ant × GitHub Contributions.

Generates self-contained, lightweight, high-fidelity SVGs (light & dark mode)
animating Langton's Ant traversing the contribution graph with pure CSS keyframes.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

from scripts.langton_sim import (
    CalendarCell,
    CalendarData,
    SimulationResult,
    DIR_ANGLES,
    DIR_NAMES,
)

# Dimensions matching standard GitHub contribution calendars
CELL_SIZE = 11.0  # size of dot/cell
CELL_GAP = 3.0    # gap between cells
STEP_PITCH = CELL_SIZE + CELL_GAP  # 14.0 px per coordinate unit
CORNER_RADIUS = 2.0

# Margins and paddings
PAD_LEFT = 32.0   # room for weekday labels (Seg, Qua, Sex)
PAD_TOP = 30.0    # room for month labels and header telemetry
PAD_RIGHT = 16.0
PAD_BOTTOM = 22.0 # room for status legend

# GitHub color palette (5 intensity levels: 0..4)
LIGHT_PALETTE = {
    "bg": "#ffffff",
    "border": "#e1e4e8",
    "text": "#24292f",
    "text_muted": "#57606a",
    "cell_0": "#ebedf0",
    "cell_1": "#9be9a8",
    "cell_2": "#40c463",
    "cell_3": "#30a14e",
    "cell_4": "#216e39",
    "ant_body": "#0969da",
    "ant_glow": "rgba(9, 105, 218, 0.4)",
    "ant_trail": "#0969da",
    "flip_active": "#2da44e",
    "flip_inactive": "#d0d7de",
    "accent": "#0969da",
}

DARK_PALETTE = {
    "bg": "#0d1117",
    "border": "#30363d",
    "text": "#e6edf3",
    "text_muted": "#7d8590",
    "cell_0": "#161b22",
    "cell_1": "#0e4429",
    "cell_2": "#006d32",
    "cell_3": "#26a641",
    "cell_4": "#39d353",
    "ant_body": "#58a6ff",
    "ant_glow": "rgba(88, 166, 255, 0.45)",
    "ant_trail": "#58a6ff",
    "flip_active": "#3fb950",
    "flip_inactive": "#21262d",
    "accent": "#58a6ff",
}

MONTH_NAMES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
WEEKDAY_LABELS = [(1, "Seg"), (3, "Qua"), (5, "Sex")]  # Mon, Wed, Fri
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, 'Helvetica Neue', Helvetica, Arial, sans-serif"


def get_cell_level_index(level: str) -> int:
    mapping = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }
    return mapping.get(level, 0)


def render_langton_svg(
    calendar: CalendarData,
    simulation: SimulationResult,
    theme: str = "light",
    duration_s: float = 14.0,
) -> str:
    """Renders a complete, deterministic, standalone animated SVG for Langton's Ant."""
    palette = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE

    weeks_count = max(calendar.weeks_count, 53)
    grid_width = weeks_count * STEP_PITCH - CELL_GAP
    grid_height = 7 * STEP_PITCH - CELL_GAP

    svg_width = int(math.ceil(PAD_LEFT + grid_width + PAD_RIGHT))
    svg_height = int(math.ceil(PAD_TOP + grid_height + PAD_BOTTOM))

    total_steps = len(simulation.steps)
    if total_steps == 0:
        total_steps = 1

    # Coordinate mapping: from grid (x, y) to absolute SVG (px, py)
    def to_svg_xy(gx: float, gy: float) -> Tuple[float, float]:
        return (PAD_LEFT + gx * STEP_PITCH, PAD_TOP + gy * STEP_PITCH)

    # 1. Base calendar rects
    # Identify which cells are flipped during the simulation and at what normalized times
    cell_first_visit: Dict[Tuple[int, int], List[float]] = {}
    for step in simulation.steps:
        pos = (step.x, step.y)
        if 0 <= step.x < weeks_count and 0 <= step.y < 7:
            t = step.step_index / total_steps
            cell_first_visit.setdefault(pos, []).append(t)

    # Build month header labels
    month_labels: List[Tuple[float, str]] = []
    last_month = None
    for w in range(weeks_count):
        cell = calendar.cells.get((w, 0))
        if cell and cell.date:
            m = int(cell.date.split("-")[1])
            if m != last_month:
                month_labels.append((PAD_LEFT + w * STEP_PITCH, MONTH_NAMES_PT[m - 1]))
                last_month = m

    # 2. Build Ant Animation Keyframes
    ant_keyframes: List[str] = []
    step_duration_pct = 100.0 / total_steps

    for i, step in enumerate(simulation.steps):
        t_start = i * step_duration_pct
        px, py = to_svg_xy(step.x, step.y)
        cx = px + CELL_SIZE / 2.0
        cy = py + CELL_SIZE / 2.0
        angle = DIR_ANGLES[step.direction]
        t_fmt = f"{t_start:.2f}%"
        ant_keyframes.append(f"{t_fmt} {{ transform: translate({cx:.1f}px, {cy:.1f}px) rotate({angle}deg); }}")

    # Final wrap frame
    final_step = simulation.steps[-1]
    final_px, final_py = to_svg_xy(final_step.x, final_step.y)
    final_angle = DIR_ANGLES[final_step.direction]
    ant_keyframes.append(
        f"100.00% {{ transform: translate({final_px + CELL_SIZE/2.0:.1f}px, {final_py + CELL_SIZE/2.0:.1f}px) rotate({final_angle}deg); }}"
    )

    # 3. Dynamic Cell Glow / React Keyframes
    cell_styles: List[str] = []
    cell_rects: List[str] = []

    anim_cell_counter = 0
    for w in range(weeks_count):
        for d in range(7):
            cell = calendar.cells.get((w, d))
            px, py = to_svg_xy(w, d)
            if not cell:
                continue

            lvl = get_cell_level_index(cell.level)
            base_color = palette[f"cell_{lvl}"]
            visits = cell_first_visit.get((w, d), [])

            if visits and (cell.count > 0 or len(visits) > 1):
                cid = f"c{anim_cell_counter}"
                anim_cell_counter += 1
                pulse_color = palette["accent"] if cell.count > 0 else palette["flip_active"]
                kf_rules: List[str] = [f"0% {{ fill: {base_color}; }}"]
                for v_t in visits[:4]:
                    p_start = max(0.0, v_t * 100.0 - 0.1)
                    p_peak = v_t * 100.0 + 0.8
                    p_end = min(100.0, v_t * 100.0 + 3.5)
                    kf_rules.append(f"{p_start:.2f}% {{ fill: {base_color}; }}")
                    kf_rules.append(f"{p_peak:.2f}% {{ fill: {pulse_color}; }}")
                    kf_rules.append(f"{p_end:.2f}% {{ fill: {base_color}; }}")
                kf_rules.append(f"100% {{ fill: {base_color}; }}")

                cell_styles.append(f"@keyframes {cid} {{ {' '.join(kf_rules)} }}")
                cell_styles.append(f".{cid} {{ animation: {cid} {duration_s:.1f}s linear infinite; }}")
                cell_rects.append(
                    f'<rect class="day {cid}" x="{px:.1f}" y="{py:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}" fill="{base_color}"/>'
                )
            else:
                cell_rects.append(
                    f'<rect class="day" x="{px:.1f}" y="{py:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}" fill="{base_color}"/>'
                )

    # 4. Trail path
    trail_points: List[str] = []
    for step in simulation.steps:
        px, py = to_svg_xy(step.x, step.y)
        cx = px + CELL_SIZE / 2.0
        cy = py + CELL_SIZE / 2.0
        trail_points.append(f"{cx:.1f},{cy:.1f}")
    trail_points_str = " ".join(trail_points)

    # 5. Telemetry / Metadata header
    highway_str = f" · HIGHWAY p={simulation.highway_period}" if simulation.highway_detected else ""
    telemetry_left = f"LANGTON'S ANT · REGRA RL · {calendar.total_contributions} CONTRIBUIÇÕES REAIS{highway_str}"
    telemetry_right = f"ORIGEM: W{simulation.start_x:02d}:D{simulation.start_y} [{DIR_NAMES[simulation.start_dir]}] · {total_steps} PASSOS"

    # Assemble CSS
    css = f"""
    svg {{
      font-family: {FONT_STACK};
      font-size: 9px;
      user-select: none;
    }}
    .bg {{ fill: {palette['bg']}; stroke: {palette['border']}; stroke-width: 1px; rx: 6px; }}
    .lbl-title {{ fill: {palette['accent']}; font-weight: 600; font-size: 9px; letter-spacing: 0.5px; }}
    .lbl-sub {{ fill: {palette['text_muted']}; font-size: 8.5px; }}
    .lbl-axis {{ fill: {palette['text_muted']}; font-size: 8.5px; }}
    .trail {{
      fill: none;
      stroke: {palette['ant_trail']};
      stroke-width: 1.2px;
      stroke-linecap: round;
      stroke-linejoin: round;
      opacity: 0.35;
    }}
    .ant-agent {{
      animation: ant-walk {duration_s:.1f}s linear infinite;
      will-change: transform;
    }}
    .ant-body {{
      fill: {palette['ant_body']};
      filter: drop-shadow(0 0 2px {palette['ant_glow']});
    }}
    .ant-eye {{ fill: #ffffff; }}
    @keyframes ant-walk {{
      {" ".join(ant_keyframes)}
    }}
    {" ".join(cell_styles)}
    @media (prefers-reduced-motion: reduce) {{
      .ant-agent, .day {{ animation: none !important; }}
      .trail {{ opacity: 0.5; }}
    }}
    """

    # Weekday label elements
    weekday_elements = []
    for d_idx, text in WEEKDAY_LABELS:
        wy = PAD_TOP + d_idx * STEP_PITCH + CELL_SIZE - 2.0
        weekday_elements.append(
            f'<text class="lbl-axis" x="{PAD_LEFT - 6.0:.1f}" y="{wy:.1f}" text-anchor="end">{text}</text>'
        )

    # Month label elements
    month_elements = []
    for mx, text in month_labels:
        month_elements.append(
            f'<text class="lbl-axis" x="{mx:.1f}" y="{PAD_TOP - 8.0:.1f}">{text}</text>'
        )

    # Legend at bottom right
    legend_x = svg_width - PAD_RIGHT - 110.0
    legend_y = svg_height - PAD_BOTTOM + 8.0
    legend_elements = [
        f'<text class="lbl-axis" x="{legend_x - 6.0:.1f}" y="{legend_y + 8.0:.1f}" text-anchor="end">Menos</text>'
    ]
    for i in range(5):
        lx = legend_x + i * 13.0
        c_fill = palette[f"cell_{i}"]
        legend_elements.append(
            f'<rect x="{lx:.1f}" y="{legend_y:.1f}" width="9" height="9" rx="1.5" ry="1.5" fill="{c_fill}"/>'
        )
    legend_elements.append(
        f'<text class="lbl-axis" x="{legend_x + 68.0:.1f}" y="{legend_y + 8.0:.1f}">Mais</text>'
    )

    # Ant Agent Graphic: clean cybernetic autonomous agent pointer/triangle with sensor eyes
    ant_svg = """
    <g class="ant-agent">
      <!-- Autonomous Agent Glyph (Micro Cyber-Ant) -->
      <path class="ant-body" d="M 0,-5.2 L 4.0,4.2 L 0,2.4 L -4.0,4.2 Z"/>
      <circle class="ant-eye" cx="-1.4" cy="-0.6" r="0.8"/>
      <circle class="ant-eye" cx="1.4" cy="-0.6" r="0.8"/>
    </g>
    """

    # Assemble complete SVG
    svg_content = f"""<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <title>Langton's Ant × GitHub Contributions ({theme.capitalize()})</title>
  <desc>Deterministic Langton's Ant RL simulation seeded by real GitHub contributions. Total commits: {calendar.total_contributions}.</desc>
  <!-- Generated by leozaow/leozaow Langton contribution renderer -->
  <style>
    {css}
  </style>
  <rect width="100%" height="100%" class="bg"/>

  <!-- Telemetry Header -->
  <text class="lbl-title" x="{PAD_LEFT:.1f}" y="{PAD_TOP - 18.0:.1f}">{telemetry_left}</text>
  <text class="lbl-sub" x="{svg_width - PAD_RIGHT:.1f}" y="{PAD_TOP - 18.0:.1f}" text-anchor="end">{telemetry_right}</text>

  <!-- Month Labels -->
  {"".join(month_elements)}

  <!-- Weekday Labels -->
  {"".join(weekday_elements)}

  <!-- Contribution Grid Cells -->
  <g id="calendar-grid">
    {"".join(cell_rects)}
  </g>

  <!-- Trajectory Trail -->
  <polyline class="trail" points="{trail_points_str}"/>

  <!-- Langton Ant Agent -->
  {ant_svg}

  <!-- Footer Legend -->
  <text class="lbl-sub" x="{PAD_LEFT:.1f}" y="{svg_height - PAD_BOTTOM + 16.0:.1f}">Autômato Celular 2D · Regra RL (0: Dir, 1: Esq) · Grid Infinito Esparso</text>
  {"".join(legend_elements)}
</svg>"""

    return svg_content
