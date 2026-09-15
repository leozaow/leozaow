#!/usr/bin/env python3
"""Langton's Ant simulation engine for GitHub contribution graphs (V3).

Implements the classic 2D Langton's Ant automaton with RL rules on an infinite
sparse grid, seeded by a GitHub contribution calendar.
Supports deep multi-thousand step simulations and window slice execution.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


# Directions in (dx, dy) where x is week (0..52), y is day of week (0..6, Sunday=0)
# 0: North (y - 1)
# 1: East  (x + 1)
# 2: South (y + 1)
# 3: West  (x - 1)
DIRECTIONS = [
    (0, -1),  # 0: North
    (1, 0),   # 1: East
    (0, 1),   # 2: South
    (-1, 0),  # 3: West
]

DIR_NAMES = ["N", "E", "S", "W"]
DIR_ANGLES = [0, 90, 180, 270]  # Degrees pointing along direction vector


@dataclass(frozen=True)
class CalendarCell:
    x: int  # week index (0..52)
    y: int  # day index (0..6)
    date: str
    count: int
    level: str  # NONE, FIRST_QUARTILE, SECOND_QUARTILE, THIRD_QUARTILE, FOURTH_QUARTILE


@dataclass
class CalendarData:
    total_contributions: int
    weeks_count: int
    cells: Dict[Tuple[int, int], CalendarCell]
    min_date: str
    max_date: str


@dataclass
class AntStep:
    step_index: int
    x: int
    y: int
    direction_before: int  # arrival direction (facing when arriving at cell)
    turn_direction: str    # "R" or "L"
    direction_after: int   # departure direction (pointing towards next cell)
    cell_state_before: int # 0 or 1
    cell_state_after: int  # 1 or 0 (flipped)
    is_calendar_cell: bool
    is_original_commit: bool
    commit_count: int


@dataclass
class SimulationResult:
    start_x: int
    start_y: int
    start_dir: int
    window_start: int
    window_end: int
    steps: List[AntStep]
    initial_grid_snapshot: Dict[Tuple[int, int], int]  # grid state at window_start
    final_grid_snapshot: Dict[Tuple[int, int], int]    # grid state at window_end
    visited_cells: Set[Tuple[int, int]]
    highway_detected: bool = False
    highway_period: int = 0
    highway_dx: int = 0
    highway_dy: int = 0
    highway_verified_cycles: int = 0
    highway_start_step: Optional[int] = None


class LangtonSimulation:
    """Simulates Langton's Ant on an infinite sparse plane seeded by a contribution calendar."""

    def __init__(self, initial_grid: Optional[Dict[Tuple[int, int], int]] = None):
        self.grid: Dict[Tuple[int, int], int] = dict(initial_grid) if initial_grid else {}

    def get_state(self, x: int, y: int) -> int:
        return self.grid.get((x, y), 0)

    def set_state(self, x: int, y: int, state: int) -> None:
        if state == 0:
            self.grid.pop((x, y), None)
        else:
            self.grid[(x, y)] = 1

    def run(
        self,
        start_x: int,
        start_y: int,
        start_dir: int,
        max_steps: int,
        calendar: Optional[CalendarData] = None,
        record_window: Optional[Tuple[int, int]] = None,
    ) -> SimulationResult:
        """Runs the simulation for max_steps from (start_x, start_y) facing start_dir.

        If record_window is given as (w_start, w_end), steps are only recorded in that range
        to preserve CPU memory during multi-thousand deep simulations.
        """
        x = start_x
        y = start_y
        direction = start_dir % 4

        w_start, w_end = record_window if record_window else (0, max_steps)
        steps: List[AntStep] = []
        visited_cells: Set[Tuple[int, int]] = set()
        initial_window_grid: Dict[Tuple[int, int], int] = {}
        all_recorded_positions: List[Tuple[int, int, int]] = []  # (x, y, dir_after) for highway check

        for step_idx in range(max_steps):
            if step_idx == w_start:
                initial_window_grid = dict(self.grid)

            state_before = self.get_state(x, y)
            dir_before = direction

            # Classic RL rule:
            if state_before == 0:
                turn = "R"
                dir_after = (dir_before + 1) & 3
                state_after = 1
            else:
                turn = "L"
                dir_after = (dir_before - 1) & 3
                state_after = 0

            self.set_state(x, y, state_after)

            if w_start <= step_idx < w_end:
                visited_cells.add((x, y))
                is_cal = False
                is_commit = False
                c_count = 0
                if calendar:
                    cell = calendar.cells.get((x, y))
                    if cell:
                        is_cal = True
                        is_commit = cell.count > 0
                        c_count = cell.count

                steps.append(
                    AntStep(
                        step_index=step_idx,
                        x=x,
                        y=y,
                        direction_before=dir_before,
                        turn_direction=turn,
                        direction_after=dir_after,
                        cell_state_before=state_before,
                        cell_state_after=state_after,
                        is_calendar_cell=is_cal,
                        is_original_commit=is_commit,
                        commit_count=c_count,
                    )
                )

            # Record for highway checking
            all_recorded_positions.append((x, y, dir_after))

            direction = dir_after
            dx, dy = DIRECTIONS[direction]
            x += dx
            y += dy

        final_window_grid = dict(self.grid)

        # Rigorous Highway Detection
        hw_detected, hw_period, hw_dx, hw_dy, hw_cycles, hw_start = detect_highway_rigorous(
            all_recorded_positions, min_repeats=3
        )

        return SimulationResult(
            start_x=start_x,
            start_y=start_y,
            start_dir=start_dir % 4,
            window_start=w_start,
            window_end=w_end,
            steps=steps,
            initial_grid_snapshot=initial_window_grid,
            final_grid_snapshot=final_window_grid,
            visited_cells=visited_cells,
            highway_detected=hw_detected,
            highway_period=hw_period,
            highway_dx=hw_dx,
            highway_dy=hw_dy,
            highway_verified_cycles=hw_cycles,
            highway_start_step=hw_start,
        )


def detect_highway_rigorous(
    history: List[Tuple[int, int, int]],  # (x, y, dir_after)
    min_repeats: int = 3,
) -> Tuple[bool, int, int, int, int, Optional[int]]:
    """Rigorously detects translational highway with at least min_repeats consecutive periods.

    Returns: (detected, period, dx, dy, verified_cycles, start_step)
    """
    n = len(history)
    for p in [104, 52]:
        needed = p * min_repeats
        if n < needed:
            continue

        # Check last cycle displacement
        dx_base = history[-1][0] - history[-1 - p][0]
        dy_base = history[-1][1] - history[-1 - p][1]
        if dx_base == 0 and dy_base == 0:
            continue  # stationary cycle

        # Check all steps in the last min_repeats cycles
        valid = True
        for cycle in range(1, min_repeats):
            offset = cycle * p
            for i in range(n - 1 - offset, n - 1 - offset - p, -1):
                if i - p < 0:
                    valid = False
                    break
                dx = history[i][0] - history[i - p][0]
                dy = history[i][1] - history[i - p][1]
                dir1 = history[i][2]
                dir2 = history[i - p][2]
                if dx != dx_base or dy != dy_base or dir1 != dir2:
                    valid = False
                    break
            if not valid:
                break

        if valid:
            # Count total verified consecutive cycles backward
            total_cycles = min_repeats
            curr_tail = n - 1 - (min_repeats * p)
            while curr_tail - p >= 0:
                cycle_ok = True
                for j in range(curr_tail, curr_tail - p, -1):
                    dx = history[j][0] - history[j - p][0]
                    dy = history[j][1] - history[j - p][1]
                    if dx != dx_base or dy != dy_base or history[j][2] != history[j - p][2]:
                        cycle_ok = False
                        break
                if cycle_ok:
                    total_cycles += 1
                    curr_tail -= p
                else:
                    break

            start_estimate = curr_tail
            return True, p, dx_base, dy_base, total_cycles, start_estimate

    return False, 0, 0, 0, 0, None


def parse_contribution_calendar(payload: dict) -> CalendarData:
    """Parses GitHub GraphQL contribution calendar data into structured CalendarData."""
    data = payload.get("data", payload)
    user_data = data.get("user", {})
    coll = user_data.get("contributionsCollection", {})
    cal = coll.get("contributionCalendar", {})

    total_contributions = cal.get("totalContributions", 0)
    weeks = cal.get("weeks", [])
    weeks_count = len(weeks)

    cells: Dict[Tuple[int, int], CalendarCell] = {}
    all_dates: List[str] = []

    for w_idx, week in enumerate(weeks):
        for d_idx, day in enumerate(week.get("contributionDays", [])):
            d_str = day.get("date", "")
            count = day.get("contributionCount", 0)
            level = day.get("contributionLevel", "NONE")
            if d_str:
                all_dates.append(d_str)

            cells[(w_idx, d_idx)] = CalendarCell(
                x=w_idx,
                y=d_idx,
                date=d_str,
                count=count,
                level=level,
            )

    all_dates.sort()
    min_date = all_dates[0] if all_dates else ""
    max_date = all_dates[-1] if all_dates else ""

    return CalendarData(
        total_contributions=total_contributions,
        weeks_count=weeks_count,
        cells=cells,
        min_date=min_date,
        max_date=max_date,
    )


def seed_grid_from_calendar(calendar: CalendarData) -> Dict[Tuple[int, int], int]:
    """Builds initial binary grid: 1 if contributionCount > 0, else 0 (omitted from sparse dict)."""
    grid: Dict[Tuple[int, int], int] = {}
    for (x, y), cell in calendar.cells.items():
        if cell.count > 0:
            grid[(x, y)] = 1
    return grid


def get_candidate_origins(calendar: CalendarData) -> List[Tuple[int, int]]:
    """Deterministically identifies candidate starting positions across all active cells and key centers."""
    active_cells = [(pos, cell) for pos, cell in calendar.cells.items() if cell.count > 0]
    candidates: List[Tuple[int, int]] = []

    max_w = calendar.weeks_count if calendar.weeks_count > 0 else 53
    candidates.append((max_w // 2, 3))

    if not active_cells:
        candidates.append((max_w // 2 - 2, 3))
        candidates.append((max_w // 2 + 2, 3))
        return list(dict.fromkeys(candidates))

    # All active cells sorted by date
    sorted_active = sorted(active_cells, key=lambda it: it[1].date)
    for pos, _ in sorted_active:
        candidates.append(pos)

    # Weighted centroid
    total_weight = sum(math.log1p(c.count) for _, c in active_cells)
    if total_weight > 0:
        wx_sum = sum(pos[0] * math.log1p(c.count) for pos, c in active_cells)
        wy_sum = sum(pos[1] * math.log1p(c.count) for pos, c in active_cells)
        cx = int(round(wx_sum / total_weight))
        cy = int(round(wy_sum / total_weight))
        candidates.append((cx, cy))

    return list(dict.fromkeys(candidates))
