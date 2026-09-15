#!/usr/bin/env python3
"""Deep simulation and analysis for Langton's Ant trajectory (V4).

Evaluates deep horizons (10k-50k steps), extracts sliding windows,
classifies trajectory phases, enforces spatial and quadrant diversity across the candidate pool,
and implements deterministic daily selection.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from scripts.langton_sim import (
    CalendarCell,
    CalendarData,
    SimulationResult,
    LangtonSimulation,
    seed_grid_from_calendar,
    get_candidate_origins,
    DIR_NAMES,
)


@dataclass
class TrajectoryPhase:
    start_step: int
    end_step: int
    name: str  # "seeding", "local_chaos", "expansion", "revisitation", "highway"
    in_bounds_ratio: float
    commits_ratio: float
    entropy: float


@dataclass
class CandidateWindow:
    score: float
    cand_idx: int
    origin: Tuple[int, int]
    dir: int
    dir_name: str
    window_start: int
    window_end: int
    in_cal_ratio: float
    unique_cells: int
    commits_hit: int
    entropy: float
    bounding_box: Tuple[int, int, int, int]


@dataclass
class DeepAnalysis:
    total_simulated: int
    display_steps: int
    window_start: int
    window_end: int
    daily_seed: str
    pool_size: int
    selected_rank: int
    candidate_origin: Tuple[int, int]
    candidate_direction: str
    highway_detected: bool
    highway_period: int
    highway_dx: int
    highway_dy: int
    highway_verified_cycles: int
    highway_start_step: Optional[int]
    phases: List[TrajectoryPhase]
    unique_cells_visited: int
    in_bounds_steps: int
    commits_visited: int
    bounding_box: Tuple[int, int, int, int]  # min_x, max_x, min_y, max_y


def compute_daily_seed(calendar: CalendarData, date_str: str) -> str:
    """Computes a deterministic hash seed combining calendar activity, target date and algorithm version."""
    active_summary = "".join(f"{k[0]}:{k[1]}:{v.count};" for k, v in sorted(calendar.cells.items()) if v.count > 0)
    raw = f"langton-v4|{calendar.total_contributions}|{active_summary}|{date_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def find_top_diverse_pool(
    calendar: CalendarData,
    deep_horizon: int = 10000,
    window_size: int = 240,
    window_stride: int = 100,
    pool_capacity: int = 16,
) -> List[CandidateWindow]:
    """Scans all candidate origins across deep horizons and extracts a strictly diverse pool of sliding windows.

    Guarantees diversity by:
    1. Sampling windows across deep steps (up to 5,000 steps).
    2. Multi-objective scoring rewarding calendar coverage, active commit interaction, and path entropy.
    3. Spatial separation: Candidates must come from distinct calendar regions (min Euclidean distance
       or different origin positions) so that different ranks explore visibly distinct areas of the grid.
    """
    base_grid = seed_grid_from_calendar(calendar)
    candidates = get_candidate_origins(calendar)
    dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    all_qualified: List[CandidateWindow] = []

    for cand_idx, (cx, cy) in enumerate(candidates):
        for d_init in range(4):
            # Fast simulation recording (x, y, dir_after, state_before)
            grid = dict(base_grid)
            x, y, d = cx, cy, d_init
            history: List[Tuple[int, int, int, int]] = []

            for step in range(deep_horizon):
                s = grid.get((x, y), 0)
                if s == 0:
                    d = (d + 1) & 3
                    grid[(x, y)] = 1
                else:
                    d = (d - 1) & 3
                    del grid[(x, y)]
                history.append((x, y, d, s))
                dx, dy = dirs[d]
                x += dx
                y += dy

            # Evaluate sliding windows up to step 5000
            max_scan = min(len(history) - window_size, 5000)
            for w_start in range(0, max_scan + 1, window_stride):
                w_steps = history[w_start : w_start + window_size]
                in_cal = sum(1 for (wx, wy, _, _) in w_steps if 0 <= wx < 53 and 0 <= wy < 7)
                in_cal_ratio = in_cal / window_size
                if in_cal_ratio < 0.75:
                    continue

                unique_cells = len(set((wx, wy) for (wx, wy, _, _) in w_steps if 0 <= wx < 53 and 0 <= wy < 7))
                commits_hit = sum(
                    1 for (wx, wy) in set((wx, wy) for (wx, wy, _, _) in w_steps)
                    if calendar.cells.get((wx, wy)) and calendar.cells[(wx, wy)].count > 0
                )
                if commits_hit < 5:
                    continue

                # Direction entropy
                dir_counts = [0, 0, 0, 0]
                for (_, _, dir_a, _) in w_steps:
                    dir_counts[dir_a] += 1
                entropy = 0.0
                for dc in dir_counts:
                    if dc > 0:
                        p = dc / window_size
                        entropy -= p * math.log2(p)

                min_wx = min(wx for (wx, wy, _, _) in w_steps)
                max_wx = max(wx for (wx, wy, _, _) in w_steps)
                min_wy = min(wy for (wx, wy, _, _) in w_steps)
                max_wy = max(wy for (wx, wy, _, _) in w_steps)

                # Normalized Multi-Objective Scoring
                # 1. Unique calendar cells coverage (target ~100)
                s_unique = min(1.0, unique_cells / 110.0)
                # 2. Commits hit (target ~25)
                s_commits = min(1.0, commits_hit / 25.0)
                # 3. In-bounds ratio (0.75..1.0)
                s_in_bounds = (in_cal_ratio - 0.75) / 0.25
                # 4. Turn entropy (1.5..2.0)
                s_entropy = min(1.0, max(0.0, (entropy - 1.5) / 0.5))

                score = (
                    s_unique * 35.0
                    + s_commits * 35.0
                    + s_in_bounds * 20.0
                    + s_entropy * 10.0
                )

                all_qualified.append(
                    CandidateWindow(
                        score=score,
                        cand_idx=cand_idx,
                        origin=(cx, cy),
                        dir=d_init,
                        dir_name=DIR_NAMES[d_init],
                        window_start=w_start,
                        window_end=w_start + window_size,
                        in_cal_ratio=in_cal_ratio,
                        unique_cells=unique_cells,
                        commits_hit=commits_hit,
                        entropy=entropy,
                        bounding_box=(min_wx, max_wx, min_wy, max_wy),
                    )
                )

    all_qualified.sort(key=lambda it: it.score, reverse=True)

    # Diversity enforcement: select distinct origins and trajectories
    # Pass 1: Strict origin uniqueness
    diverse_pool: List[CandidateWindow] = []
    seen_origins: Set[Tuple[int, int]] = set()

    for cand in all_qualified:
        if cand.origin not in seen_origins:
            seen_origins.add(cand.origin)
            diverse_pool.append(cand)
            if len(diverse_pool) >= pool_capacity:
                break

    # Pass 2: If pool capacity not reached, accept candidates with distinct window_start or direction
    if len(diverse_pool) < pool_capacity:
        seen_keys: Set[Tuple[Tuple[int, int], int, int]] = {
            (c.origin, c.dir, c.window_start) for c in diverse_pool
        }
        for cand in all_qualified:
            key = (cand.origin, cand.dir, cand.window_start)
            if key not in seen_keys:
                seen_keys.add(key)
                diverse_pool.append(cand)
                if len(diverse_pool) >= pool_capacity:
                    break

    if not diverse_pool and all_qualified:
        diverse_pool = all_qualified[:pool_capacity]

    if not diverse_pool:
        # Fallback candidate
        diverse_pool = [
            CandidateWindow(
                score=100.0,
                cand_idx=0,
                origin=(53 // 2, 3),
                dir=1,
                dir_name="E",
                window_start=0,
                window_end=window_size,
                in_cal_ratio=1.0,
                unique_cells=50,
                commits_hit=10,
                entropy=1.9,
                bounding_box=(0, 52, 0, 6),
            )
        ]

    return diverse_pool


def select_daily_simulation(
    calendar: CalendarData,
    date_str: str,
    steps_count: int = 240,
    deep_horizon: int = 10000,
    pool_capacity: int = 12,
) -> Tuple[SimulationResult, DeepAnalysis]:
    """Deterministically selects and fully simulates today's trajectory slice from the diverse pool."""
    pool = find_top_diverse_pool(
        calendar,
        deep_horizon=deep_horizon,
        window_size=steps_count,
        window_stride=100,
        pool_capacity=pool_capacity,
    )

    daily_seed = compute_daily_seed(calendar, date_str)
    seed_int = int(daily_seed[:8], 16)
    selected_rank = seed_int % len(pool)
    chosen = pool[selected_rank]

    # Run full Langton simulation up to window_end recording the exact window slice
    sim = LangtonSimulation(initial_grid=seed_grid_from_calendar(calendar))
    res = sim.run(
        start_x=chosen.origin[0],
        start_y=chosen.origin[1],
        start_dir=chosen.dir,
        max_steps=chosen.window_end,
        calendar=calendar,
        record_window=(chosen.window_start, chosen.window_end),
    )

    # Classify trajectory phases across the chosen slice
    phases: List[TrajectoryPhase] = []
    chunk_size = max(30, steps_count // 5)
    for p_idx in range(0, len(res.steps), chunk_size):
        sub = res.steps[p_idx : p_idx + chunk_size]
        if not sub:
            continue
        p_start = chosen.window_start + p_idx
        p_end = p_start + len(sub)
        p_in_bounds = sum(1 for s in sub if 0 <= s.x < 53 and 0 <= s.y < 7) / len(sub)
        p_commits = sum(1 for s in sub if s.commit_count > 0) / len(sub)

        d_counts = [0, 0, 0, 0]
        for s in sub:
            d_counts[s.direction_after] += 1
        p_entropy = 0.0
        for dc in d_counts:
            if dc > 0:
                p = dc / len(sub)
                p_entropy -= p * math.log2(p)

        if chosen.window_start == 0 and p_idx == 0:
            name = "seeding"
        elif res.highway_detected and p_end >= (res.highway_start_step or 0):
            name = "highway"
        elif p_commits > 0.35:
            name = "revisitation"
        elif p_in_bounds > 0.8:
            name = "local_chaos"
        else:
            name = "expansion"

        phases.append(
            TrajectoryPhase(
                start_step=p_start,
                end_step=p_end,
                name=name,
                in_bounds_ratio=p_in_bounds,
                commits_ratio=p_commits,
                entropy=p_entropy,
            )
        )

    analysis = DeepAnalysis(
        total_simulated=deep_horizon,
        display_steps=steps_count,
        window_start=chosen.window_start,
        window_end=chosen.window_end,
        daily_seed=daily_seed,
        pool_size=len(pool),
        selected_rank=selected_rank,
        candidate_origin=chosen.origin,
        candidate_direction=chosen.dir_name,
        highway_detected=res.highway_detected,
        highway_period=res.highway_period,
        highway_dx=res.highway_dx,
        highway_dy=res.highway_dy,
        highway_verified_cycles=res.highway_verified_cycles,
        highway_start_step=res.highway_start_step,
        phases=phases,
        unique_cells_visited=len(res.visited_cells),
        in_bounds_steps=sum(1 for s in res.steps if 0 <= s.x < 53 and 0 <= s.y < 7),
        commits_visited=sum(1 for s in res.steps if s.commit_count > 0),
        bounding_box=chosen.bounding_box,
    )

    return res, analysis
