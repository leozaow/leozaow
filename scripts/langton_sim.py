#!/usr/bin/env python3
"""Langton's Ant simulation engine for GitHub contribution graphs (V2).

Implements the classic 2D Langton's Ant automaton with RL rules on an infinite
sparse grid, seeded by a GitHub contribution calendar.
"""

from __future__ import annotations

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
    steps: List[AntStep]
    final_grid: Dict[Tuple[int, int], int]
    visited_cells: Set[Tuple[int, int]]
    highway_detected: bool = False
    highway_period: int = 0


class LangtonSimulation:
    """Simulates Langton's Ant on an infinite sparse plane seeded by a contribution calendar."""

    def __init__(self, initial_grid: Optional[Dict[Tuple[int, int], int]] = None):
        # Sparse grid storing binary state: 0 (inactive/white) or 1 (active/black)
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
    ) -> SimulationResult:
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

        for step_idx in range(max_steps):
            visited_cells.add((x, y))
            state_before = self.get_state(x, y)
            dir_before = direction

            # RL rule:
            if state_before == 0:
                turn = "R"
                dir_after = (dir_before + 1) % 4
                state_after = 1
            else:
                turn = "L"
                dir_after = (dir_before - 1) % 4
                state_after = 0

            # Flip cell in the infinite sparse grid
            self.set_state(x, y, state_after)

            # Metadata for calendar tracking
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

            # Move to next cell
            direction = dir_after
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
            highway_detected=highway_detected,
            highway_period=period,
        )


def detect_highway(steps: List[AntStep], min_repeats: int = 2) -> Tuple[bool, int]:
    """Detects if the trajectory has entered a periodic translational highway (e.g. period 104)."""
    n = len(steps)
    if n < 208:
        return False, 0

    for p in [104, 52]:
        if n < p * min_repeats:
            continue
        dx_base = steps[-1].x - steps[-1 - p].x
        dy_base = steps[-1].y - steps[-1 - p].y
        if dx_base == 0 and dy_base == 0:
            continue  # Pure cycle, not highway

        is_highway = True
        for i in range(n - 1, n - 1 - p, -1):
            dx = steps[i].x - steps[i - p].x
            dy = steps[i].y - steps[i - p].y
            dir1 = steps[i].direction_after
            dir2 = steps[i - p].direction_after
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
    """Deterministically identifies candidate starting positions.

    Tests all active contribution cells (up to 40), geometric center, centroid,
    and high-density cluster centers.
    """
    active_cells = [(pos, cell) for pos, cell in calendar.cells.items() if cell.count > 0]
    candidates: List[Tuple[int, int]] = []

    max_w = calendar.weeks_count if calendar.weeks_count > 0 else 53
    candidates.append((max_w // 2, 3))

    if not active_cells:
        candidates.append((max_w // 2 - 2, 3))
        candidates.append((max_w // 2 + 2, 3))
        return list(dict.fromkeys(candidates))

    # All active cells in chronological order
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


def select_best_simulation(
    calendar: CalendarData,
    steps_count: int = 240,
    deep_horizon: int = 10000,
) -> Tuple[SimulationResult, "DeepAnalysis"]:
    """Selects the best origin and trajectory using multi-scale simulation and deterministic scoring."""
    from scripts.langton_analysis import analyze_deep_simulation, score_deep_candidate

    base_grid = seed_grid_from_calendar(calendar)
    candidates = get_candidate_origins(calendar)

    best_score = -float("inf")
    best_sim: Optional[SimulationResult] = None
    best_analysis: Optional["DeepAnalysis"] = None
    best_candidate_key = None

    for cand_idx, (cx, cy) in enumerate(candidates):
        for direction in [0, 1, 2, 3]:  # N, E, S, W
            # Run deep simulation
            sim = LangtonSimulation(initial_grid=base_grid)
            res = sim.run(start_x=cx, start_y=cy, start_dir=direction, max_steps=deep_horizon, calendar=calendar)
            
            score = score_deep_candidate(res, calendar, display_steps=steps_count)

            # Deterministic tie-breaker
            key = (score, -cand_idx, -direction)
            if best_candidate_key is None or key > best_candidate_key:
                best_candidate_key = key
                best_score = score
                # Create visual slice result
                visual_sim = SimulationResult(
                    start_x=res.start_x,
                    start_y=res.start_y,
                    start_dir=res.start_dir,
                    steps=res.steps[:steps_count],
                    final_grid=res.final_grid,
                    visited_cells=set((s.x, s.y) for s in res.steps[:steps_count]),
                    highway_detected=res.highway_detected,
                    highway_period=res.highway_period,
                )
                best_sim = visual_sim
                best_analysis = analyze_deep_simulation(calendar, res, display_steps=steps_count)

    if best_sim is None or best_analysis is None:
        sim = LangtonSimulation(initial_grid=base_grid)
        res = sim.run(start_x=max_w // 2, start_y=3, start_dir=1, max_steps=steps_count, calendar=calendar)
        analysis = analyze_deep_simulation(calendar, res, display_steps=steps_count)
        return res, analysis

    return best_sim, best_analysis
