#!/usr/bin/env python3
"""Deep simulation and analysis for Langton's Ant trajectory.

Evaluates long horizons (10k-20k steps), trajectory phases, emergence,
and deterministic scoring for selecting the optimal origin and visual window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from scripts.langton_sim import (
    CalendarCell,
    CalendarData,
    SimulationResult,
    LangtonSimulation,
    detect_highway,
    seed_grid_from_calendar,
)


@dataclass
class TrajectoryPhase:
    start_step: int
    end_step: int
    name: str  # "seeding", "local_chaos", "expansion", "highway"
    in_bounds_ratio: float
    commits_ratio: float
    entropy: float


@dataclass
class DeepAnalysis:
    total_simulated: int
    display_steps: int
    highway_detected: bool
    highway_period: int
    highway_start_step: Optional[int]
    phases: List[TrajectoryPhase]
    unique_cells_visited: int
    in_bounds_steps: int
    commits_visited: int
    bounding_box: Tuple[int, int, int, int]  # min_x, max_x, min_y, max_y


def analyze_deep_simulation(
    calendar: CalendarData,
    sim_result: SimulationResult,
    display_steps: int = 240,
) -> DeepAnalysis:
    """Performs multi-scale trajectory analysis across the full simulation horizon."""
    weeks = calendar.weeks_count if calendar.weeks_count > 0 else 53
    total_sim = len(sim_result.steps)

    min_x = min(s.x for s in sim_result.steps)
    max_x = max(s.x for s in sim_result.steps)
    min_y = min(s.y for s in sim_result.steps)
    max_y = max(s.y for s in sim_result.steps)

    in_bounds_steps = sum(1 for s in sim_result.steps if 0 <= s.x < weeks and 0 <= s.y < 7)
    commits_visited = sum(
        1 for pos in sim_result.visited_cells if calendar.cells.get(pos) and calendar.cells[pos].count > 0
    )

    # Check for highway start step
    hw_start = None
    if sim_result.highway_detected and sim_result.highway_period > 0:
        p = sim_result.highway_period
        # Find earliest step where highway condition starts
        for i in range(2 * p, total_sim):
            is_hw, _ = detect_highway(sim_result.steps[:i], min_repeats=2)
            if is_hw:
                hw_start = i - 2 * p
                break

    # Analyze phases across display window
    phases: List[TrajectoryPhase] = []
    w_size = max(display_steps // 4, 30)
    for w_idx in range(0, display_steps, w_size):
        chunk = sim_result.steps[w_idx : min(w_idx + w_size, display_steps)]
        if not chunk:
            continue
        in_b = sum(1 for s in chunk if 0 <= s.x < weeks and 0 <= s.y < 7) / len(chunk)
        c_hit = sum(
            1 for s in chunk if calendar.cells.get((s.x, s.y)) and calendar.cells[(s.x, s.y)].count > 0
        ) / len(chunk)
        
        # Turn entropy
        dir_counts = [0, 0, 0, 0]
        for s in chunk:
            dir_counts[s.direction_after] += 1
        entropy = 0.0
        for dc in dir_counts:
            if dc > 0:
                p = dc / len(chunk)
                entropy -= p * math.log2(p)

        phase_name = "local_chaos"
        if w_idx == 0:
            phase_name = "seeding"
        elif in_b > 0.85 and c_hit > 0.15:
            phase_name = "revisitation"
        elif in_b < 0.60:
            phase_name = "expansion"

        phases.append(
            TrajectoryPhase(
                start_step=w_idx,
                end_step=min(w_idx + w_size, display_steps),
                name=phase_name,
                in_bounds_ratio=in_b,
                commits_ratio=c_hit,
                entropy=entropy,
            )
        )

    return DeepAnalysis(
        total_simulated=total_sim,
        display_steps=display_steps,
        highway_detected=sim_result.highway_detected,
        highway_period=sim_result.highway_period,
        highway_start_step=hw_start,
        phases=phases,
        unique_cells_visited=len(sim_result.visited_cells),
        in_bounds_steps=in_bounds_steps,
        commits_visited=commits_visited,
        bounding_box=(min_x, max_x, min_y, max_y),
    )


def score_deep_candidate(
    sim_result: SimulationResult,
    calendar: CalendarData,
    display_steps: int = 240,
) -> float:
    """Calculates comprehensive score for candidate trajectory in both short and long horizons."""
    weeks = calendar.weeks_count if calendar.weeks_count > 0 else 53
    display_chunk = sim_result.steps[:display_steps]
    if not display_chunk:
        return -1000.0

    in_bounds = sum(1 for s in display_chunk if 0 <= s.x < weeks and 0 <= s.y < 7)
    in_bounds_ratio = in_bounds / len(display_chunk)

    unique_cal = len(set((s.x, s.y) for s in display_chunk if 0 <= s.x < weeks and 0 <= s.y < 7))
    commits_hit = sum(
        1 for (x, y) in set((s.x, s.y) for s in display_chunk)
        if calendar.cells.get((x, y)) and calendar.cells[(x, y)].count > 0
    )

    # Flips: count how many state inversions occur in visible calendar
    flips_count = sum(
        1 for s in display_chunk if 0 <= s.x < weeks and 0 <= s.y < 7 and s.cell_state_before != s.cell_state_after
    )

    # Direction changes
    dir_changes = sum(
        1 for i in range(1, len(display_chunk)) if display_chunk[i].direction_after != display_chunk[i - 1].direction_after
    )

    # Escape penalty: severe if under 80% in bounds during display window
    escape_pen = max(0.0, 0.85 - in_bounds_ratio) * 250.0

    # Long-term bonus: does the candidate visit commits in the broader 10k horizon?
    deep_commits_hit = sum(
        1 for pos in sim_result.visited_cells if calendar.cells.get(pos) and calendar.cells[pos].count > 0
    )

    # Highway emergence bonus in full simulation
    highway_bonus = 35.0 if sim_result.highway_detected else 0.0

    score = (
        unique_cal * 2.2
        + commits_hit * 6.5
        + in_bounds_ratio * 70.0
        + dir_changes * 0.4
        + flips_count * 0.2
        + (deep_commits_hit / max(1, len(calendar.cells))) * 25.0
        + highway_bonus
        - escape_pen
    )

    return score
