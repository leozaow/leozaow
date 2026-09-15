#!/usr/bin/env python3
"""Langton's Ant simulation engine for GitHub contribution graphs.

Implements the classic 2D Langton's Ant automaton with RL rules on an infinite
sparse grid, seeded by a GitHub contribution calendar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


# Directions in (dx, dy) where x is week (0..52), y is day of week (0..6, Sunday=0)
# Standard cartesian:
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
DIR_ANGLES = [0, 90, 180, 270]  # Degrees with North as 0deg pointing up


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
    direction: int  # 0..3 (direction BEFORE turn, or state at arrival)
    cell_state_before: int  # 0 or 1
    cell_flipped: bool


@dataclass
class SimulationResult:
    start_x: int
    start_y: int
    start_dir: int
    steps: List[AntStep]
    final_grid: Dict[Tuple[int, int], int]
    visited_cells: Set[Tuple[int, int]]
    cells_flipped_in_calendar: Set[Tuple[int, int]]
    highway_detected: bool = False
    highway_period: int = 0


class LangtonSimulation:
    """Simulates Langton's Ant on an infinite sparse plane seeded by a contribution calendar."""

    def __init__(self, initial_grid: Optional[Dict[Tuple[int, int], int]] = None):
        # Sparse grid storing state: 0 (white/inactive) or 1 (black/active)
        self.grid: Dict[Tuple[int, int], int] = dict(initial_grid) if initial_grid else {}

    def get_state(self, x: int, y: int) -> int:
        return self.grid.get((x, y), 0)

    def set_state(self, x: int, y: int, state: int) -> None:
        if state == 0:
            self.grid.pop((x, y), None)
        else:
            self.grid[(x, y)] = 1

    def run(self, start_x: int, start_y: int, start_dir: int, max_steps: int) -> SimulationResult:
        """Runs the simulation for max_steps from (start_x, start_y) facing start_dir.

        Classic RL rule:
        - At cell with state 0: Turn RIGHT (+1 mod 4), flip to 1, move forward 1 step.
        - At cell with state 1: Turn LEFT (-1 mod 4), flip to 0, move forward 1 step.
        """
        x = start_x
        y = start_y
        direction = start_dir % 4

        steps: List[AntStep] = []
        visited_cells: Set[Tuple[int, int]] = set()
        flipped_in_cal: Set[Tuple[int, int]] = set()

        for step_idx in range(max_steps):
            visited_cells.add((x, y))
            current_state = self.get_state(x, y)

            # Record step state before movement
            steps.append(
                AntStep(
                    step_index=step_idx,
                    x=x,
                    y=y,
                    direction=direction,
                    cell_state_before=current_state,
                    cell_flipped=True,
                )
            )

            # RL rule:
            if current_state == 0:
                direction = (direction + 1) % 4  # Turn Right
                self.set_state(x, y, 1)
            else:
                direction = (direction - 1) % 4  # Turn Left
                self.set_state(x, y, 0)

            # Advance 1 step
            dx, dy = DIRECTIONS[direction]
            x += dx
            y += dy

        # Detect potential highway (periodicity by translation)
        highway_detected, period = detect_highway(steps)

        return SimulationResult(
            start_x=start_x,
            start_y=start_y,
            start_dir=start_dir % 4,
            steps=steps,
            final_grid=self.grid,
            visited_cells=visited_cells,
            cells_flipped_in_calendar=flipped_in_cal,
            highway_detected=highway_detected,
            highway_period=period,
        )


def detect_highway(steps: List[AntStep], min_repeats: int = 2) -> Tuple[bool, int]:
    """Detects if the trajectory has entered a periodic translational highway (e.g. period 104)."""
    n = len(steps)
    if n < 208:
        return False, 0

    # Common Langton highway periods: 104, 52, 208
    for p in [104, 52]:
        if n < p * min_repeats:
            continue
        # Check last p steps against previous p steps
        # Translational periodicity: pos[i] - pos[i - p] == (dx, dy) for all i in window
        dx_base = steps[-1].x - steps[-1 - p].x
        dy_base = steps[-1].y - steps[-1 - p].y
        if dx_base == 0 and dy_base == 0:
            continue  # Pure cycle, not highway

        is_highway = True
        for i in range(n - 1, n - 1 - p, -1):
            dx = steps[i].x - steps[i - p].x
            dy = steps[i].y - steps[i - p].y
            dir1 = steps[i].direction
            dir2 = steps[i - p].direction
            if dx != dx_base or dy != dy_base or dir1 != dir2:
                is_highway = False
                break

        if is_highway:
            return True, p

    return False, 0


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

            # day of week from weekday or d_idx
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
    """Deterministically identifies promising candidate starting points for the ant."""
    active_cells = [(pos, cell) for pos, cell in calendar.cells.items() if cell.count > 0]
    candidates: List[Tuple[int, int]] = []

    # 1. Geometric center of the calendar
    max_w = calendar.weeks_count if calendar.weeks_count > 0 else 53
    center_pos = (max_w // 2, 3)
    candidates.append(center_pos)

    if not active_cells:
        # Empty calendar: just center and a couple nearby positions
        candidates.append((max_w // 2 - 2, 3))
        candidates.append((max_w // 2 + 2, 3))
        return list(dict.fromkeys(candidates))

    # 2. Most recent active contribution cell
    sorted_by_date = sorted(active_cells, key=lambda item: item[1].date, reverse=True)
    candidates.append(sorted_by_date[0][0])

    # 3. Active cell closest to the weighted centroid of contributions
    total_weight = 0.0
    wx_sum = 0.0
    wy_sum = 0.0
    for (x, y), cell in active_cells:
        weight = math.log1p(cell.count)
        total_weight += weight
        wx_sum += x * weight
        wy_sum += y * weight

    if total_weight > 0:
        centroid_x = wx_sum / total_weight
        centroid_y = wy_sum / total_weight
        closest_to_centroid = min(
            active_cells,
            key=lambda item: (
                (item[0][0] - centroid_x) ** 2 + (item[0][1] - centroid_y) ** 2,
                item[0][0],
                item[0][1],
            ),
        )[0]
        candidates.append(closest_to_centroid)

    # 4. Center of highest density 5x3 window
    best_density = -1.0
    best_win_center = (max_w // 2, 3)
    for x in range(2, max_w - 2):
        for y in range(1, 6):
            # 5x3 window
            win_count = sum(
                calendar.cells.get((wx, wy), CalendarCell(wx, wy, "", 0, "NONE")).count
                for wx in range(x - 2, x + 3)
                for wy in range(y - 1, y + 2)
            )
            if win_count > best_density:
                best_density = win_count
                best_win_center = (x, y)
    candidates.append(best_win_center)

    # 5. Cell with the absolute maximum contributions
    max_cell = max(active_cells, key=lambda item: (item[1].count, item[0][0], item[0][1]))[0]
    candidates.append(max_cell)

    # Return unique candidates preserving order
    return list(dict.fromkeys(candidates))


def score_trajectory(
    sim_result: SimulationResult,
    calendar: CalendarData,
    max_steps: int,
) -> float:
    """Deterministically evaluates a simulated trajectory for visual quality on the profile.

    Higher score = more visually engaging, better calendar coverage, meaningful interaction
    with commits, and low boundary escape penalty.
    """
    weeks = calendar.weeks_count if calendar.weeks_count > 0 else 53
    unique_cells_in_bounds = 0
    unique_cells_with_commits = 0
    in_bounds_steps = 0
    direction_changes = 0

    prev_dir = None
    seen_positions: Set[Tuple[int, int]] = set()

    for step in sim_result.steps:
        pos = (step.x, step.y)
        in_bounds = (0 <= step.x < weeks) and (0 <= step.y < 7)
        if in_bounds:
            in_bounds_steps += 1
            if pos not in seen_positions:
                seen_positions.add(pos)
                unique_cells_in_bounds += 1
                cell = calendar.cells.get(pos)
                if cell and cell.count > 0:
                    unique_cells_with_commits += 1

        if prev_dir is not None and prev_dir != step.direction:
            direction_changes += 1
        prev_dir = step.direction

    total_steps = len(sim_result.steps)
    if total_steps == 0:
        return -1000.0

    in_bounds_ratio = in_bounds_steps / total_steps
    # Severe penalty if the ant escapes the calendar too quickly
    if in_bounds_ratio < 0.70:
        escape_penalty = (0.70 - in_bounds_ratio) * 200.0
    else:
        escape_penalty = 0.0

    # Coverage score
    coverage_score = unique_cells_in_bounds * 2.5
    # Commit interaction bonus
    commit_score = unique_cells_with_commits * 5.0
    # Turn diversity (avoids boring straight lines)
    turn_score = direction_changes * 0.5
    # In-bounds continuity reward
    in_bounds_reward = in_bounds_ratio * 50.0
    # Bonus for highway if detected
    highway_bonus = 25.0 if sim_result.highway_detected else 0.0

    return (
        coverage_score
        + commit_score
        + turn_score
        + in_bounds_reward
        + highway_bonus
        - escape_penalty
    )


def select_best_simulation(
    calendar: CalendarData,
    steps_count: int = 160,
) -> SimulationResult:
    """Tests all deterministic candidate origins across all 4 directions and picks the best."""
    base_grid = seed_grid_from_calendar(calendar)
    candidates = get_candidate_origins(calendar)

    best_score = -float("inf")
    best_result: Optional[SimulationResult] = None
    best_candidate_key = None

    for cand_idx, (cx, cy) in enumerate(candidates):
        for direction in [0, 1, 2, 3]:  # N, E, S, W
            # Create a fresh simulation with initial seeded grid
            sim = LangtonSimulation(initial_grid=base_grid)
            res = sim.run(start_x=cx, start_y=cy, start_dir=direction, max_steps=steps_count)
            score = score_trajectory(res, calendar, steps_count)

            # Deterministic tie-breaker: (score, -cand_idx, -direction)
            key = (score, -cand_idx, -direction)
            if best_candidate_key is None or key > best_candidate_key:
                best_candidate_key = key
                best_score = score
                best_result = res

    if best_result is None:
        # Fallback to center facing East
        weeks = calendar.weeks_count if calendar.weeks_count > 0 else 53
        sim = LangtonSimulation(initial_grid=base_grid)
        return sim.run(start_x=weeks // 2, start_y=3, start_dir=1, max_steps=steps_count)

    return best_result
