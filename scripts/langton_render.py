#!/usr/bin/env python3
"""SVG renderer for Langton's Ant × GitHub Contributions.

Renders a pure, native GitHub contribution calendar animated by Langton's Ant:
1. Native GitHub contribution calendar styling, geometry, and font metrics.
2. Clean header: minimal and dignified (no microaulas, no RL formulas, no redundant title).
3. Complete elimination of ghost cells / out-of-bounds dashed rects that caused artifacts.
4. Exact calendar clip path guaranteeing no trail or overlay escapes the 53×7 calendar bounds.
5. Subtle Langton memory: ultra-thin inner stroke (0.75px, opacity ~0.35) preserving GitHub calendar supremacy.
6. Strong Current Interaction: dynamic cell halo and sensor pulse moving with the ant.
7. Fading tail: progressive trail with tail dash limiting clutter to recent trajectory.
8. Native GitHub legend ("Menos" / "Mais").
9. 100% deterministic, standalone XML, lightweight, zero JavaScript.
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

# Layout dimensions: refined compact margins matching native GitHub contribution graph
PAD_LEFT = 32.0
PAD_TOP = 20.0
PAD_RIGHT = 16.0
PAD_BOTTOM = 22.0

# Palette specifications: native GitHub colors
LIGHT_PALETTE = {
    "bg": "#ffffff",
    "border": "#d0d7de",
    "text": "#1f2328",
    "text_muted": "#656d76",
    "cell_0": "#ebedf0",
    "cell_1": "#9be9a8",
    "cell_2": "#40c463",
    "cell_3": "#30a14e",
    "cell_4": "#216e39",
    "ant_body": "#0969da",
    "ant_eye": "#ffffff",
    "ant_glow": "rgba(9, 105, 218, 0.45)",
    "trail": "#0969da",
    "trail_glow": "rgba(9, 105, 218, 0.20)",
    "state_flip_on": "#1f883d",
    "accent": "#0969da",
}

DARK_PALETTE = {
    "bg": "#0d1117",
    "border": "#30363d",
    "text": "#f0f6fc",
    "text_muted": "#848d97",
    "cell_0": "#161b22",
    "cell_1": "#0e4429",
    "cell_2": "#006d32",
    "cell_3": "#26a641",
    "cell_4": "#39d353",
    "ant_body": "#58a6ff",
    "ant_eye": "#ffffff",
    "ant_glow": "rgba(88, 166, 255, 0.50)",
    "trail": "#58a6ff",
    "trail_glow": "rgba(88, 166, 255, 0.25)",
    "state_flip_on": "#3fb950",
    "accent": "#58a6ff",
}

MONTH_NAMES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
WEEKDAY_LABELS = [(1, "Seg"), (3, "Qua"), (5, "Sex")]
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"


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
    analysis: Optional[DeepAnalysis] = None,
    theme: str = "light",
    duration_s: float = 16.0,
) -> str:
    """Renders the standalone animated SVG for Langton's Ant with native GitHub styling."""
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

    # Fading tail length: ~30 steps = ~420 px
    tail_len = 420.0

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
    trail_keyframes.append(f"{t_ant_start:.2f}% {{ stroke-dashoffset: {total_trail_len:.1f}; opacity: 0.55; }}")

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
            f"{t_pct:.2f}% {{ stroke-dashoffset: {current_offset:.1f}; opacity: 0.55; }}"
        )

    # Wrap & Fade
    ant_keyframes.append(f"{t_ant_end:.2f}% {{ opacity: 1; }}")
    ant_keyframes.append("97.00% { opacity: 0; }")
    ant_keyframes.append("100.00% { opacity: 0; }")

    trail_keyframes.append(f"{t_ant_end:.2f}% {{ stroke-dashoffset: 0; opacity: 0.55; }}")
    trail_keyframes.append("97.00% { stroke-dashoffset: 0; opacity: 0; }")
    trail_keyframes.append(f"100.00% {{ stroke-dashoffset: {total_trail_len:.1f}; opacity: 0; }}")

    # 3. Dynamic Cell State & Overlays (Refined subtle inner stroke 0.75px, opacity ~0.35)
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
            init_state = simulation.initial_grid_snapshot.get((w, d), 1 if cell.count > 0 else 0)

            if flips or (init_state == 1 and cell.count == 0):
                cid = f"fl_{anim_cell_counter}"
                anim_cell_counter += 1

                kf_overlay: List[str] = []
                init_op = 0.35 if init_state == 1 else 0.0
                kf_overlay.append(f"0.00% {{ opacity: {init_op:.2f}; }}")
                kf_overlay.append(f"{t_ant_start:.2f}% {{ opacity: {init_op:.2f}; }}")

                for t_pct, state_after, _ in flips:
                    t_before = max(t_ant_start, t_pct - 0.05)
                    if state_after == 1:
                        kf_overlay.append(f"{t_before:.2f}% {{ opacity: 0.0; }}")
                        kf_overlay.append(f"{t_pct:.2f}% {{ opacity: 0.40; }}")
                    else:
                        kf_overlay.append(f"{t_before:.2f}% {{ opacity: 0.40; }}")
                        kf_overlay.append(f"{t_pct:.2f}% {{ opacity: 0.0; }}")

                final_state = flips[-1][1] if flips else init_state
                final_op = 0.40 if final_state == 1 else 0.0
                kf_overlay.append(f"{t_ant_end:.2f}% {{ opacity: {final_op:.2f}; }}")
                kf_overlay.append("97.00% { opacity: 0.0; }")
                kf_overlay.append("100.00% { opacity: 0.0; }")

                cell_styles.append(f"@keyframes {cid} {{ {' '.join(kf_overlay)} }}")
                cell_styles.append(
                    f".{cid} {{ animation: {cid} {duration_s:.1f}s cubic-bezier(0.2, 0, 0, 1) infinite; }}"
                )

                stroke_color = palette["state_flip_on"] if cell.count > 0 else palette["accent"]
                overlay_state_rects.append(
                    f'<rect class="state-overlay {cid}" x="{px:.1f}" y="{py:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}" ry="{CORNER_RADIUS}" fill="none" stroke="{stroke_color}" stroke-width="0.75"/>'
                )

    # 4. Month & Weekday Labels (Authentic GitHub placement)
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
        f'<text class="lbl-axis" x="{mx:.1f}" y="{PAD_TOP - 6.0:.1f}">{text}</text>'
        for mx, text in month_labels
    ]

    weekday_elements = [
        f'<text class="lbl-axis" x="{PAD_LEFT - 7.0:.1f}" y="{PAD_TOP + d_idx * STEP_PITCH + CELL_SIZE - 2.0:.1f}" text-anchor="end">{text}</text>'
        for d_idx, text in WEEKDAY_LABELS
    ]

    css = f"""
    svg {{
      font-family: {FONT_STACK};
      font-size: 9px;
      user-select: none;
    }}
    .bg {{ fill: {palette['bg']}; stroke: {palette['border']}; stroke-width: 1px; rx: 6px; }}
    .lbl-axis {{ fill: {palette['text_muted']}; font-size: 8.5px; }}
    .trail {{
      fill: none;
      stroke: {palette['trail']};
      stroke-width: 1.2px;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: {tail_len:.1f} {total_trail_len:.1f};
      filter: drop-shadow(0 0 1px {palette['trail_glow']});
      animation: trail-reveal {duration_s:.1f}s linear infinite;
    }}
    .state-overlay {{
      opacity: 0;
      will-change: opacity;
    }}
    .ant-agent {{
      animation: ant-walk {duration_s:.1f}s linear infinite;
      will-change: transform, opacity;
    }}
    .ant-halo {{
      fill: none;
      stroke: {palette['accent']};
      stroke-width: 1.5px;
      opacity: 0.85;
      filter: drop-shadow(0 0 3px {palette['ant_glow']});
    }}
    .ant-body {{
      fill: {palette['ant_body']};
      filter: drop-shadow(0 0 2.5px {palette['ant_glow']});
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
      .trail {{ stroke-dashoffset: 0 !important; opacity: 0.30 !important; }}
      .state-overlay {{ opacity: 0.35 !important; }}
    }}
    """

    ant_svg = f"""
    <g class="ant-agent">
      <!-- Active cell interaction halo (Current Interaction) -->
      <rect class="ant-halo" x="{-CELL_SIZE/2.0:.1f}" y="{-CELL_SIZE/2.0:.1f}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="{CORNER_RADIUS}"/>
      <!-- Autonomous Agent Silhouette -->
      <line class="ant-antenna" x1="-1.6" y1="-3.0" x2="-3.2" y2="-6.0"/>
      <line class="ant-antenna" x1="1.6" y1="-3.0" x2="3.2" y2="-6.0"/>
      <path class="ant-body" d="M 0,-4.5 L 3.2,2.6 L 0,1.2 L -3.2,2.6 Z"/>
      <circle class="ant-body" cx="0" cy="4.0" r="2.0"/>
      <circle class="ant-eye" cx="-1.1" cy="-1.6" r="0.7"/>
      <circle class="ant-eye" cx="1.1" cy="-1.6" r="0.7"/>
    </g>
    """

    # Native GitHub Legend ("Menos" [5 rects] "Mais")
    legend_x = svg_width - PAD_RIGHT - 105.0
    legend_y = svg_height - PAD_BOTTOM + 6.0
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
  <title>Langton's Ant × GitHub Contributions ({theme.capitalize()})</title>
  <desc>Deterministic Langton's Ant RL simulation seeded by real GitHub contributions. Total commits: {calendar.total_contributions}.</desc>
  <!-- Generated by leozaow/leozaow Langton contribution renderer V4 Refined -->
  <defs>
    <!-- Calendar Clip: strictly clips dynamic animation layers to the 53x7 calendar grid -->
    <clipPath id="calendar-clip">
      <rect x="{PAD_LEFT:.1f}" y="{PAD_TOP:.1f}" width="{grid_width:.1f}" height="{grid_height:.1f}" rx="{CORNER_RADIUS}"/>
    </clipPath>
  </defs>
  <style>
    {css}
  </style>
  <rect width="100%" height="100%" class="bg"/>

  <!-- Month Labels -->
  {"".join(month_elements)}

  <!-- Weekday Labels -->
  {"".join(weekday_elements)}

  <!-- Data Layer: Base Contribution Calendar -->
  <g id="calendar-data-layer">
    {"".join(base_calendar_rects)}
  </g>

  <!-- Dynamic Layers (Clipped strictly to calendar canvas) -->
  <g id="calendar-dynamic-layer" clip-path="url(#calendar-clip)">
    <!-- Automaton State Layer: Dynamically Flipped Overlays -->
    <g id="automaton-state-layer">
      {"".join(overlay_state_rects)}
    </g>

    <!-- Fading Tail Trail -->
    <path class="trail" d="{path_d}"/>

    <!-- Autonomous Agent with Current Interaction Halo -->
    {ant_svg}
  </g>

  <!-- Footer Micro-Legend -->
  {"".join(legend_elements)}
</svg>"""

    return svg_content


# Backward compatibility alias
render_langton_svg_v3 = render_langton_svg
