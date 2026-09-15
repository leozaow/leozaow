#!/usr/bin/env python3
"""SVG renderer for Langton's Ant × GitHub Contributions (V3).

Generates a self-contained, high-fidelity, living animated SVG (light & dark mode)
featuring:
1. Dual-layer visualization: original GitHub contributions + dynamic Langton state overlays.
2. Progressive trail emergence via synchronized CSS dashoffset (no pre-drawn path).
3. Cybernetic micro-ant with visible orientation, head, body, and sensory pulse.
4. Active cell interaction with persisting state flips and glow proportional to commits.
5. Rich metadata telemetry reflecting the exact simulation window slice and daily seed.
6. 100% deterministic, standalone XML, lightweight, zero JavaScript.
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
from scripts.langton_analysis import DeepAnalysis

# Grid dimensions matching GitHub standard layout
CELL_SIZE = 11.0
CELL_GAP = 3.0
STEP_PITCH = CELL_SIZE + CELL_GAP  # 14.0 px
CORNER_RADIUS = 2.0

# Layout dimensions with extra room for ghost bounds and elegant headers
PAD_LEFT = 34.0
PAD_TOP = 32.0
PAD_RIGHT = 16.0
PAD_BOTTOM = 26.0

# Palette specifications
LIGHT_PALETTE = {
    "bg": "#ffffff",
    "border": "#d0d7de",
    "text": "#24292f",
    "text_muted": "#57606a",
    "cell_0": "#ebedf0",
    "cell_1": "#9be9a8",
    "cell_2": "#40c463",
    "cell_3": "#30a14e",
    "cell_4": "#216e39",
    "ant_body": "#0969da",
    "ant_eye": "#ffffff",
    "ant_glow": "rgba(9, 105, 218, 0.45)",
    "trail": "#0969da",
    "trail_glow": "rgba(9, 105, 218, 0.25)",
    "state_flip_on": "#1f883d",
    "state_flip_off": "#afb8c1",
    "accent": "#0969da",
    "ghost_cell": "rgba(235, 237, 240, 0.6)",
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
    "ant_eye": "#ffffff",
    "ant_glow": "rgba(88, 166, 255, 0.55)",
    "trail": "#58a6ff",
    "trail_glow": "rgba(88, 166, 255, 0.35)",
    "state_flip_on": "#3fb950",
    "state_flip_off": "#30363d",
    "accent": "#58a6ff",
    "ghost_cell": "rgba(22, 27, 34, 0.6)",
}

MONTH_NAMES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
WEEKDAY_LABELS = [(1, "Seg"), (3, "Qua"), (5, "Sex")]
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


def render_langton_svg_v3(
    calendar: CalendarData,
    simulation: SimulationResult,
    analysis: Optional[DeepAnalysis] = None,
    theme: str = "light",
    duration_s: float = 16.0,
) -> str:
    """Renders the V3 standalone animated SVG for Langton's Ant with window slice tracking."""
    palette = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE
    weeks_count = max(calendar.weeks_count, 53)

    grid_width = weeks_count * STEP_PITCH - CELL_GAP
    grid_height = 7 * STEP_PITCH - CELL_GAP

    svg_width = int(math.ceil(PAD_LEFT + grid_width + PAD_RIGHT))
    svg_height = int(math.ceil(PAD_TOP + grid_height + PAD_BOTTOM))

    total_steps = len(simulation.steps)
    if total_steps == 0:
        total_steps = 1

    def to_svg_xy(gx: float, gy: float) -> Tuple[float, float]:
        return (PAD_LEFT + gx * STEP_PITCH, PAD_TOP + gy * STEP_PITCH)

    # 1. Coordinate Trail & Path Length Calculation
    path_segments: List[Tuple[float, float]] = []
    cum_lengths: List[float] = [0.0]

    for step in simulation.steps:
        px, py = to_svg_xy(step.x, step.y)
        cx = px + CELL_SIZE / 2.0
        cy = py + CELL_SIZE / 2.0
        if path_segments:
            prev_cx, prev_cy = path_segments[-1]
            seg_len = math.hypot(cx - prev_cx, cy - prev_cy)
            cum_lengths.append(cum_lengths[-1] + seg_len)
        path_segments.append((cx, cy))

    total_trail_len = cum_lengths[-1] if cum_lengths else 1.0

    # Path d string
    path_d_parts = [f"M {path_segments[0][0]:.1f},{path_segments[0][1]:.1f}"]
    for cx, cy in path_segments[1:]:
        path_d_parts.append(f"L {cx:.1f},{cy:.1f}")
    path_d = " ".join(path_d_parts)

    # 2. Timeline Phases (0%..3% Seeding, 3%..92% Traversal, 92%..97% Pattern display, 97%..100% Reset)
    t_ant_start = 3.0
    t_ant_end = 92.0
    t_ant_span = t_ant_end - t_ant_start

    ant_keyframes: List[str] = []
    trail_keyframes: List[str] = []

    start_cx, start_cy = path_segments[0]
    start_angle = DIR_ANGLES[simulation.steps[0].direction_after]
    ant_keyframes.append(
        f"0.00% {{ transform: translate({start_cx:.1f}px, {start_cy:.1f}px) rotate({start_angle}deg); opacity: 0; }}"
    )
    ant_keyframes.append(
        f"{t_ant_start:.2f}% {{ transform: translate({start_cx:.1f}px, {start_cy:.1f}px) rotate({start_angle}deg); opacity: 1; }}"
    )

    trail_keyframes.append(f"0.00% {{ stroke-dashoffset: {total_trail_len:.1f}; opacity: 0; }}")
    trail_keyframes.append(f"{t_ant_start:.2f}% {{ stroke-dashoffset: {total_trail_len:.1f}; opacity: 0.85; }}")

    for i, step in enumerate(simulation.steps):
        frac = i / (total_steps - 1) if total_steps > 1 else 1.0
        t_pct = t_ant_start + frac * t_ant_span
        cx, cy = path_segments[i]
        angle = DIR_ANGLES[step.direction_after]

        ant_keyframes.append(
            f"{t_pct:.2f}% {{ transform: translate({cx:.1f}px, {cy:.1f}px) rotate({angle}deg); opacity: 1; }}"
        )
        current_offset = total_trail_len - cum_lengths[i]
        trail_keyframes.append(
            f"{t_pct:.2f}% {{ stroke-dashoffset: {current_offset:.1f}; opacity: 0.85; }}"
        )

    # Wrap & Fade
    ant_keyframes.append(f"{t_ant_end:.2f}% {{ opacity: 1; }}")
    ant_keyframes.append("97.00% { opacity: 0; }")
    ant_keyframes.append("100.00% { opacity: 0; }")

    trail_keyframes.append(f"{t_ant_end:.2f}% {{ stroke-dashoffset: 0; opacity: 0.85; }}")
    trail_keyframes.append("97.00% { stroke-dashoffset: 0; opacity: 0; }")
    trail_keyframes.append(f"100.00% {{ stroke-dashoffset: {total_trail_len:.1f}; opacity: 0; }}")

    # 3. Dynamic Cell State & Overlays (Persistent Flips)
    cell_steps_map: Dict[Tuple[int, int], List[Tuple[float, int, int]]] = {}
    for i, step in enumerate(simulation.steps):
        frac = i / (total_steps - 1) if total_steps > 1 else 1.0
        t_pct = t_ant_start + frac * t_ant_span
        pos = (step.x, step.y)
        cell_steps_map.setdefault(pos, []).append((t_pct, step.cell_state_after, step.commit_count))

    cell_styles: List[str] = []
    base_calendar_rects: List[str] = []
    overlay_state_rects: List[str] = []

    anim_cell_counter = 0
    for w in range(weeks_count):
        for d in range(7):
            cell = calendar.cells.get((w, d))
            px, py = to_svg_xy(w, d)
            if not cell:
                continue

            lvl = get_cell_level_index(cell.level)
            base_fill = palette[f"cell_{lvl}"]
            base_calendar_rects.append(
                f'<rect class="day" x="{px:.1f}" y="{py:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}" fill="{base_fill}"/>'
            )

            flips = cell_steps_map.get((w, d), [])
            # Initial state at start of window slice
            init_state = simulation.initial_grid_snapshot.get((w, d), 1 if cell.count > 0 else 0)

            if flips or (init_state == 1 and cell.count == 0):
                cid = f"fl_{anim_cell_counter}"
                anim_cell_counter += 1

                kf_overlay: List[str] = []
                init_op = 1 if init_state == 1 else 0
                kf_overlay.append(f"0.00% {{ opacity: {init_op}; transform: scale(1.0); }}")
                kf_overlay.append(f"{t_ant_start:.2f}% {{ opacity: {init_op}; transform: scale(1.0); }}")

                for t_pct, state_after, _ in flips:
                    t_before = max(t_ant_start, t_pct - 0.05)
                    if state_after == 1:
                        kf_overlay.append(f"{t_before:.2f}% {{ opacity: 0; transform: scale(0.85); }}")
                        kf_overlay.append(f"{t_pct:.2f}% {{ opacity: 1; transform: scale(1.0); }}")
                    else:
                        kf_overlay.append(f"{t_before:.2f}% {{ opacity: 1; transform: scale(1.0); }}")
                        kf_overlay.append(f"{t_pct:.2f}% {{ opacity: 0; transform: scale(0.85); }}")

                final_state = flips[-1][1] if flips else init_state
                final_op = 1 if final_state == 1 else 0
                kf_overlay.append(f"{t_ant_end:.2f}% {{ opacity: {final_op}; }}")
                kf_overlay.append("97.00% { opacity: 0; }")
                kf_overlay.append("100.00% { opacity: 0; }")

                cell_styles.append(f"@keyframes {cid} {{ {' '.join(kf_overlay)} }}")
                cell_styles.append(
                    f".{cid} {{ animation: {cid} {duration_s:.1f}s cubic-bezier(0.2, 0, 0, 1) infinite; transform-origin: {px + CELL_SIZE/2.0:.1f}px {py + CELL_SIZE/2.0:.1f}px; }}"
                )

                stroke_color = palette["state_flip_on"] if cell.count > 0 else palette["accent"]
                overlay_state_rects.append(
                    f'<rect class="state-overlay {cid}" x="{px:.1f}" y="{py:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}" fill="none" stroke="{stroke_color}" stroke-width="1.4"/>'
                )

    # 4. Ghost Grid for Out-of-Bounds Steps
    ghost_rects: List[str] = []
    seen_oob: Set[Tuple[int, int]] = set()
    for step in simulation.steps:
        if not (0 <= step.x < weeks_count and 0 <= step.y < 7):
            pos = (step.x, step.y)
            if pos not in seen_oob and (-4 <= step.x <= weeks_count + 4) and (-4 <= step.y <= 10):
                seen_oob.add(pos)
                gpx, gpy = to_svg_xy(step.x, step.y)
                ghost_rects.append(
                    f'<rect class="ghost-cell" x="{gpx:.1f}" y="{gpy:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}"/>'
                )

    # 5. Month & Weekday Labels
    month_labels: List[Tuple[float, str]] = []
    last_month = None
    for w in range(weeks_count):
        cell = calendar.cells.get((w, 0))
        if cell and cell.date:
            m = int(cell.date.split("-")[1])
            if m != last_month:
                month_labels.append((PAD_LEFT + w * STEP_PITCH, MONTH_NAMES_PT[m - 1]))
                last_month = m

    month_elements = [
        f'<text class="lbl-axis" x="{mx:.1f}" y="{PAD_TOP - 9.0:.1f}">{text}</text>'
        for mx, text in month_labels
    ]

    weekday_elements = [
        f'<text class="lbl-axis" x="{PAD_LEFT - 7.0:.1f}" y="{PAD_TOP + d_idx * STEP_PITCH + CELL_SIZE - 2.0:.1f}" text-anchor="end">{text}</text>'
        for d_idx, text in WEEKDAY_LABELS
    ]

    # 6. Telemetry & Micro-Legend
    w_start = simulation.window_start
    w_end = simulation.window_end
    window_label = f"PASSOS {w_start:04d}–{w_end:04d}"
    if w_start > 0:
        window_label += " [JANELA EVOLUÍDA]"

    hw_label = f" · HIGHWAY p={analysis.highway_period}" if (analysis and analysis.highway_detected) else ""
    telemetry_left = f"LANGTON'S ANT V3 · {calendar.total_contributions} CONTRIBUIÇÕES REAIS{hw_label}"
    telemetry_right = f"ORIGEM: W{simulation.start_x:02d}:D{simulation.start_y} [{DIR_NAMES[simulation.start_dir]}] · {window_label}"

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
    .ghost-cell {{ fill: {palette['ghost_cell']}; stroke: {palette['border']}; stroke-dasharray: 2,2; stroke-width: 0.6px; }}
    .trail {{
      fill: none;
      stroke: {palette['trail']};
      stroke-width: 1.6px;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: {total_trail_len:.1f};
      filter: drop-shadow(0 0 1.5px {palette['trail_glow']});
      animation: trail-reveal {duration_s:.1f}s linear infinite;
    }}
    .state-overlay {{
      opacity: 0;
      will-change: opacity, transform;
    }}
    .ant-agent {{
      animation: ant-walk {duration_s:.1f}s linear infinite;
      will-change: transform, opacity;
    }}
    .ant-body {{
      fill: {palette['ant_body']};
      filter: drop-shadow(0 0 3px {palette['ant_glow']});
    }}
    .ant-antenna {{
      stroke: {palette['ant_body']};
      stroke-width: 0.8px;
      stroke-linecap: round;
    }}
    .ant-eye {{ fill: {palette['ant_eye']}; }}
    @keyframes ant-walk {{
      {" ".join(ant_keyframes)}
    }}
    @keyframes trail-reveal {{
      {" ".join(trail_keyframes)}
    }}
    {" ".join(cell_styles)}
    @media (prefers-reduced-motion: reduce) {{
      .ant-agent, .trail, .state-overlay {{ animation: none !important; }}
      .trail {{ stroke-dashoffset: 0 !important; opacity: 0.45 !important; }}
      .state-overlay {{ opacity: 0.75 !important; }}
    }}
    """

    ant_svg = f"""
    <g class="ant-agent">
      <!-- Cybernetic Autonomous Agent (Ant V3) -->
      <line class="ant-antenna" x1="-1.6" y1="-3.0" x2="-3.2" y2="-6.2"/>
      <line class="ant-antenna" x1="1.6" y1="-3.0" x2="3.2" y2="-6.2"/>
      <path class="ant-body" d="M 0,-4.8 L 3.4,2.8 L 0,1.2 L -3.4,2.8 Z"/>
      <circle class="ant-body" cx="0" cy="4.2" r="2.2"/>
      <circle class="ant-eye" cx="-1.2" cy="-1.8" r="0.75"/>
      <circle class="ant-eye" cx="1.2" cy="-1.8" r="0.75"/>
    </g>
    """

    legend_x = svg_width - PAD_RIGHT - 110.0
    legend_y = svg_height - PAD_BOTTOM + 9.0
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

    svg_content = f"""<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <title>Langton's Ant × GitHub Contributions V3 ({theme.capitalize()})</title>
  <desc>Deterministic Langton's Ant RL simulation seeded by real GitHub contributions. Total commits: {calendar.total_contributions}.</desc>
  <!-- Generated by leozaow/leozaow Langton contribution renderer V3 -->
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

  <!-- Ghost Cells (Infinite Sparse Plane Glimpse) -->
  <g id="ghost-grid">
    {"".join(ghost_rects)}
  </g>

  <!-- Data Layer: Base Contribution Calendar -->
  <g id="calendar-data-layer">
    {"".join(base_calendar_rects)}
  </g>

  <!-- Automaton State Layer: Dynamically Flipped Overlays -->
  <g id="automaton-state-layer">
    {"".join(overlay_state_rects)}
  </g>

  <!-- Progressive Emergence Trail -->
  <path class="trail" d="{path_d}"/>

  <!-- Autonomous Agent (Langton's Ant V3) -->
  {ant_svg}

  <!-- Footer Micro-Legend & Rule Telemetry -->
  <text class="lbl-sub" x="{PAD_LEFT:.1f}" y="{svg_height - PAD_BOTTOM + 18.0:.1f}">Regra RL: 0 ↻ (+90° Dir, 0→1) · 1 ↺ (-90° Esq, 1→0) · Grid Infinito Esparso</text>
  {"".join(legend_elements)}
</svg>"""

    return svg_content
