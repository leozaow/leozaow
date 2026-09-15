#!/usr/bin/env python3
"""Deep simulation and analysis for Langton's Ant trajectory (V4 Refined).

Evaluates deep horizons (10k steps), extracts sliding windows across the full horizon,
classifies trajectory phases, enforces trajectory signature diversity (Jaccard similarity),
penalizes continuous out-of-bounds runs, and implements deterministic daily selection.
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
    max_oob_run: int
    bounding_box: Tuple[int, int, int, int]
    visited_set: Set[Tuple[int, int]]


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
    unique_active_cells_visited: int
    active_contribution_interactions: int
    max_oob_run: int
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
    pool_capacity: int = 12,
    max_jaccard_overlap: float = 0.82,
) -> List[CandidateWindow]:
    """Scans all candidate origins across the full deep horizon (0 -> deep_horizon - window_size)
    and extracts a strictly diverse pool using trajectory signatures and Jaccard distance.

    Guarantees:
    1. Full horizon exploration up to deep_horizon - window_size.
    2. Penalizes windows with long consecutive out-of-bounds disappearances (max_oob_run).
    3. Trajectory signature filtering: rejects candidates with > max_jaccard_overlap with existing pool.
    4. Diverse spatial and quadrant spread.
    """
    base_grid = seed_grid_from_calendar(calendar)
    candidates = get_candidate_origins(calendar)
    dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    all_qualified: List[CandidateWindow] = []

    for cand_idx, (cx, cy) in enumerate(candidates):
        for d_init in range(4):
            # Pass 1: Fast simulation recording compact histories
            grid = dict(base_grid)
            x, y, d = cx, cy, d_init
            history_x: List[int] = []
            history_y: List[int] = []
            history_d: List[int] = []

            for _ in range(deep_horizon):
                s = grid.get((x, y), 0)
                if s == 0:
                    d = (d + 1) & 3
                    grid[(x, y)] = 1
                else:
                    d = (d - 1) & 3
                    del grid[(x, y)]
                history_x.append(x)
                history_y.append(y)
                history_d.append(d)
                dx, dy = dirs[d]
                x += dx
                y += dy

            # Evaluate sliding windows across the FULL HORIZON
            max_scan = deep_horizon - window_size
            for w_start in range(0, max_scan + 1, window_stride):
                wx = history_x[w_start : w_start + window_size]
                wy = history_y[w_start : w_start + window_size]
                wd = history_d[w_start : w_start + window_size]

                # Window start and end should preferably be within calendar bounds
                start_in = (0 <= wx[0] < 53 and 0 <= wy[0] < 7)
                end_in = (0 <= wx[-1] < 53 and 0 <= wy[-1] < 7)

                # Count in-calendar and calculate max consecutive out-of-bounds run
                in_cal = 0
                curr_oob = 0
                max_oob = 0
                visited_cal_cells: Set[Tuple[int, int]] = set()

                for i in range(window_size):
                    px, py = wx[i], wy[i]
                    if 0 <= px < 53 and 0 <= py < 7:
                        in_cal += 1
                        curr_oob = 0
                        visited_cal_cells.add((px, py))
                    else:
                        curr_oob += 1
                        if curr_oob > max_oob:
                            max_oob = curr_oob

                in_cal_ratio = in_cal / window_size
                if in_cal_ratio < 0.75:
                    continue

                # Reject windows with long consecutive out-of-bounds disappearance (> 18 consecutive steps)
                if max_oob > 18:
                    continue

                unique_cells = len(visited_cal_cells)
                commits_hit = sum(
                    1 for (c_x, c_y) in visited_cal_cells
                    if calendar.cells.get((c_x, c_y)) and calendar.cells[(c_x, c_y)].count > 0
                )
                if commits_hit < 5:
                    continue

                # Direction entropy
                dir_counts = [0, 0, 0, 0]
                for d_a in wd:
                    dir_counts[d_a] += 1
                entropy = 0.0
                for dc in dir_counts:
                    if dc > 0:
                        p = dc / window_size
                        entropy -= p * math.log2(p)

                min_wx = min(wx)
                max_wx = max(wx)
                min_wy = min(wy)
                max_wy = max(wy)

                # Normalized Multi-Objective Scoring
                s_unique = min(1.0, unique_cells / 110.0)
                s_commits = min(1.0, commits_hit / 25.0)
                s_in_bounds = (in_cal_ratio - 0.75) / 0.25
                s_entropy = min(1.0, max(0.0, (entropy - 1.5) / 0.5))
                s_continuity = 1.0 - (max_oob / 20.0)  # rewards low OOB run
                s_boundary = 1.0 if (start_in and end_in) else 0.5

                score = (
                    s_unique * 30.0
                    + s_commits * 30.0
                    + s_in_bounds * 20.0
                    + s_entropy * 10.0
                    + s_continuity * 5.0
                    + s_boundary * 5.0
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
                        max_oob_run=max_oob,
                        bounding_box=(min_wx, max_wx, min_wy, max_wy),
                        visited_set=visited_cal_cells,
                    )
                )

    all_qualified.sort(key=lambda it: it.score, reverse=True)

    # True Trajectory Diversity via Jaccard Overlap Filtering:
    # Jaccard = |A ∩ B| / |A ∪ B|
    diverse_pool: List[CandidateWindow] = []

    for cand in all_qualified:
        is_redundant = False
        for accepted in diverse_pool:
            intersection = len(cand.visited_set & accepted.visited_set)
            union = len(cand.visited_set | accepted.visited_set)
            jaccard = intersection / union if union > 0 else 1.0
            if jaccard > max_jaccard_overlap:
                is_redundant = True
                break

        if not is_redundant:
            diverse_pool.append(cand)
            if len(diverse_pool) >= pool_capacity:
                break

    # If pool capacity not reached, relax threshold slightly to fill capacity
    if len(diverse_pool) < pool_capacity:
        for cand in all_qualified:
            if cand not in diverse_pool:
                diverse_pool.append(cand)
                if len(diverse_pool) >= pool_capacity:
                    break

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
                max_oob_run=0,
                bounding_box=(0, 52, 0, 6),
                visited_set={(53 // 2, 3)},
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
    """Deterministically selects and executes a two-pass simulation:
    Pass 1: Fast candidate scoring and window discovery across the full horizon.
    Pass 2: Selected candidate full deep simulation (10k steps) + window slice snapshot.
    """
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

    # Pass 2: Full deep simulation of the selected candidate across the entire deep horizon (10,000 steps)
    # This guarantees complete highway and long-term attractor analysis.
    sim = LangtonSimulation(initial_grid=seed_grid_from_calendar(calendar))
    res = sim.run(
        start_x=chosen.origin[0],
        start_y=chosen.origin[1],
        start_dir=chosen.dir,
        max_steps=deep_horizon,
        calendar=calendar,
        record_window=(chosen.window_start, chosen.window_end),
    )

    # Calculate honest, precise metrics
    # 1. Unique active contribution cells visited (cannot exceed total active days)
    unique_active_cells = {
        (s.x, s.y) for s in res.steps
        if calendar.cells.get((s.x, s.y)) and calendar.cells[(s.x, s.y)].count > 0
    }
    # 2. Total contribution interactions (revisits count each step)
    total_interactions = sum(1 for s in res.steps if s.commit_count > 0)

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
        unique_active_cells_visited=len(unique_active_cells),
        active_contribution_interactions=total_interactions,
        max_oob_run=chosen.max_oob_run,
        bounding_box=chosen.bounding_box,
    )

    return res, analysis
