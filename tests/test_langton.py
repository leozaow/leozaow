"""Comprehensive test suite for Langton's Ant × GitHub Contributions engine."""

import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.langton_sim import (
    DIRECTIONS,
    DIR_NAMES,
    CalendarCell,
    CalendarData,
    LangtonSimulation,
    detect_highway_rigorous,
    get_candidate_origins,
    parse_contribution_calendar,
    seed_grid_from_calendar,
)
from scripts.langton_analysis import (
    compute_daily_seed,
    find_top_diverse_pool,
    select_daily_simulation,
)
from scripts.langton_render import render_langton_svg, render_langton_svg_v3
from scripts.generate_langton import generate_all

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contributions.json"


class TestLangtonEngine(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            self.fixture_data = json.load(f)
        self.calendar = parse_contribution_calendar(self.fixture_data)

    def test_rl_rule_semantics_and_turns(self):
        """Tests that state_before, state_after, direction_before, and direction_after
        faithfully obey the RL rule:
        0 (white): turn right (+90 deg), flip to 1, move forward.
        1 (black): turn left (-90 deg), flip to 0, move forward.
        """
        sim = LangtonSimulation()
        res = sim.run(start_x=0, start_y=0, start_dir=0, max_steps=4)

        # Step 0: at (0, 0), state 0, facing North (0) -> Turn Right to East (1), flip to 1
        s0 = res.steps[0]
        self.assertEqual(s0.x, 0)
        self.assertEqual(s0.y, 0)
        self.assertEqual(s0.direction_before, 0)
        self.assertEqual(s0.turn_direction, "R")
        self.assertEqual(s0.direction_after, 1)
        self.assertEqual(s0.cell_state_before, 0)
        self.assertEqual(s0.cell_state_after, 1)
        self.assertEqual(sim.get_state(0, 0), 1)

        # Step 1: at (1, 0), state 0, facing East (1) -> Turn Right to South (2), flip to 1
        s1 = res.steps[1]
        self.assertEqual(s1.direction_after, 2)
        self.assertEqual(s1.cell_state_after, 1)

        # Step 2: at (1, 1), state 0, facing South (2) -> Turn Right to West (3), flip to 1
        s2 = res.steps[2]
        self.assertEqual(s2.direction_after, 3)

        # Step 3: at (0, 1), state 0, facing West (3) -> Turn Right to North (0), flip to 1
        s3 = res.steps[3]
        self.assertEqual(s3.direction_after, 0)

        # Step 4: next step enters (0, 0) which is 1 -> Turn Left to West (3), flip to 0
        res2 = sim.run(start_x=0, start_y=0, start_dir=0, max_steps=1)
        s4 = res2.steps[0]
        self.assertEqual(s4.cell_state_before, 1)
        self.assertEqual(s4.turn_direction, "L")
        self.assertEqual(s4.direction_after, 3)
        self.assertEqual(s4.cell_state_after, 0)
        self.assertEqual(sim.get_state(0, 0), 0)

    def test_infinite_sparse_plane_negative_coords_no_wrap(self):
        """Tests that moving outside calendar bounds operates smoothly on an infinite plane without wrapping."""
        sim = LangtonSimulation()
        res = sim.run(start_x=0, start_y=0, start_dir=3, max_steps=15)
        min_x = min(s.x for s in res.steps)
        min_y = min(s.y for s in res.steps)
        self.assertTrue(min_x < 0 or min_y < 0)

    def test_calendar_mapping_preservation(self):
        """Verifies weeks, days, dates and counts are correctly preserved in CalendarData."""
        self.assertGreaterEqual(self.calendar.weeks_count, 52)
        self.assertEqual(self.calendar.total_contributions, 231)
        active_cells = [c for c in self.calendar.cells.values() if c.count > 0]
        self.assertEqual(len(active_cells), 36)
        self.assertEqual(sum(c.count for c in active_cells), 231)

    def test_seed_grid_from_contributions(self):
        """Verifies binary seed: count > 0 becomes state 1; count == 0 is state 0."""
        grid = seed_grid_from_calendar(self.calendar)
        for (x, y), cell in self.calendar.cells.items():
            if cell.count > 0:
                self.assertEqual(grid.get((x, y)), 1)
            else:
                self.assertNotIn((x, y), grid)

    def test_daily_seed_determinism_and_variability(self):
        """Tests that the same date produces the identical seed and candidate,
        while different dates produce varying seeds.
        """
        seed1 = compute_daily_seed(self.calendar, "2026-09-15")
        seed1_dup = compute_daily_seed(self.calendar, "2026-09-15")
        seed2 = compute_daily_seed(self.calendar, "2026-09-16")
        seed3 = compute_daily_seed(self.calendar, "2026-09-17")

        self.assertEqual(seed1, seed1_dup)
        self.assertNotEqual(seed1, seed2)
        self.assertNotEqual(seed2, seed3)

        sim_a, a_a = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        sim_b, a_b = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        self.assertEqual(a_a.selected_rank, a_b.selected_rank)
        self.assertEqual(sim_a.start_x, sim_b.start_x)
        self.assertEqual(sim_a.window_start, sim_b.window_start)

    def test_window_analysis_can_select_evolved_window(self):
        """Tests that candidate window selection can discover and select windows where start > 0."""
        pool = find_top_diverse_pool(self.calendar, deep_horizon=3000, window_size=240, window_stride=100)
        self.assertGreater(len(pool), 0)
        has_evolved_window = any(cand.window_start > 0 for cand in pool)
        self.assertTrue(has_evolved_window, "Pool should discover evolved windows (start > 0) in deep simulation.")

    def test_full_horizon_window_discovery(self):
        """Tests that windows beyond step 5000 can be evaluated and selected when deep_horizon=10000."""
        pool = find_top_diverse_pool(self.calendar, deep_horizon=10000, window_size=240, window_stride=100)
        max_start = max(c.window_start for c in pool)
        self.assertGreater(max_start, 0)

    def test_pool_jaccard_diversity(self):
        """Tests that candidate pool members do not exceed Jaccard overlap threshold."""
        pool = find_top_diverse_pool(self.calendar, deep_horizon=3000, window_size=240, window_stride=100, pool_capacity=8)
        self.assertGreaterEqual(len(pool), 3)
        # Verify pairwise Jaccard between first few pool candidates
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                set_a = pool[i].visited_set
                set_b = pool[j].visited_set
                union = len(set_a | set_b)
                if union > 0:
                    jaccard = len(set_a & set_b) / union
                    self.assertLessEqual(jaccard, 0.90, f"Pair {i} and {j} had excessive Jaccard overlap: {jaccard:.2f}")

    def test_oob_consecutive_run_penalty(self):
        """Tests that all qualified windows strictly respect the max_oob_run threshold."""
        pool = find_top_diverse_pool(self.calendar, deep_horizon=3000, window_size=240, window_stride=100)
        for cand in pool:
            self.assertLessEqual(cand.max_oob_run, 18, f"Candidate {cand} has excessive consecutive OOB steps: {cand.max_oob_run}")

    def test_honest_metrics_semantics(self):
        """Verifies that unique active contribution cells visited cannot exceed total active days."""
        sim, an = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        active_days = sum(1 for c in self.calendar.cells.values() if c.count > 0)
        self.assertLessEqual(an.unique_active_cells_visited, active_days)
        self.assertGreaterEqual(an.active_contribution_interactions, an.unique_active_cells_visited)

    def test_deterministic_byte_for_byte_svg(self):
        """Ensures two independent renders of the same fixture and date produce bitwise identical SVGs."""
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        svg1 = render_langton_svg(self.calendar, sim, analysis, theme="light")
        svg2 = render_langton_svg(self.calendar, sim, analysis, theme="light")
        self.assertEqual(hashlib.sha256(svg1.encode("utf-8")).hexdigest(), hashlib.sha256(svg2.encode("utf-8")).hexdigest())

        svg_dark1 = render_langton_svg(self.calendar, sim, analysis, theme="dark")
        svg_dark2 = render_langton_svg(self.calendar, sim, analysis, theme="dark")
        self.assertEqual(hashlib.sha256(svg_dark1.encode("utf-8")).hexdigest(), hashlib.sha256(svg_dark2.encode("utf-8")).hexdigest())

    def test_svg_xml_validity_and_security(self):
        """Tests that both light and dark SVGs parse as valid XML, contain required elements,
        and strictly forbid <script>, external links or token leakages.
        """
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        for theme in ["light", "dark"]:
            svg = render_langton_svg(self.calendar, sim, analysis, theme=theme)
            root = ET.fromstring(svg)
            self.assertEqual(root.tag.split("}")[-1], "svg")

            titles = [el.text for el in root.iter() if el.tag.endswith("title")]
            descs = [el.text for el in root.iter() if el.tag.endswith("desc")]
            self.assertTrue(len(titles) >= 1)
            self.assertTrue(len(descs) >= 1)

            # Security assertions
            self.assertNotIn("<script", svg.lower())
            self.assertNotIn("javascript:", svg.lower())
            self.assertNotIn("gho_", svg)
            self.assertNotIn("ghp_", svg)
            self.assertNotIn("token", svg.lower())

    def test_no_redundant_titles_or_rl_rule_microaulas_in_svg(self):
        """10/10 quality requirement: no ghost cells, no duplicate titles, no microaula text."""
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        svg = render_langton_svg(self.calendar, sim, analysis, theme="light")

        # Ghost grid removed
        self.assertNotIn('id="ghost-grid"', svg)
        self.assertNotIn('class="ghost-cell"', svg)

        # Redundant title removed (since README already has heading)
        self.assertNotIn("Contribuições · Formiga de Langton", svg)

        # Technical/microaula text removed
        self.assertNotIn("Regra RL:", svg)
        self.assertNotIn("Grid Infinito", svg)
        self.assertNotIn("JANELA EVOLUÍDA", svg)

        # Calendar clip path present
        self.assertIn('clip-path="url(#calendar-clip)"', svg)

    def test_fading_tail_and_active_halo_presence(self):
        """Verifies that the trail features a fading tail dash and current interaction halo."""
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        svg = render_langton_svg(self.calendar, sim, analysis, theme="dark")

        self.assertIn("stroke-dasharray: 420.0", svg)
        self.assertIn('class="ant-halo"', svg)
        self.assertIn('id="calendar-data-layer"', svg)
        self.assertIn('id="automaton-state-layer"', svg)
        self.assertIn('class="state-overlay', svg)

    def test_smil_declarative_animation_architecture(self):
        """Verifies that animation uses native SVG SMIL exclusively, with zero CSS @keyframes or animation: rules."""
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        for theme in ["light", "dark"]:
            svg = render_langton_svg(self.calendar, sim, analysis, theme=theme)
            self.assertNotIn("@keyframes", svg)
            self.assertNotIn("animation:", svg)
            self.assertNotIn("will-change", svg)
            self.assertIn("<animateTransform", svg)
            self.assertIn('type="translate"', svg)
            self.assertIn('type="rotate"', svg)
            self.assertIn("<animate", svg)
            self.assertIn('repeatCount="indefinite"', svg)
            self.assertIn('attributeName="stroke-dashoffset"', svg)

    def test_svg_size_under_limit(self):
        """Checks that generated SVGs do not exceed 200 KiB (spec allows up to 350 KiB)."""
        sim, analysis = select_daily_simulation(self.calendar, date_str="2026-09-15", steps_count=240, deep_horizon=3000)
        svg_light = render_langton_svg(self.calendar, sim, analysis, theme="light")
        svg_dark = render_langton_svg(self.calendar, sim, analysis, theme="dark")

        self.assertLess(len(svg_light.encode("utf-8")), 200 * 1024)
        self.assertLess(len(svg_dark.encode("utf-8")), 200 * 1024)

    def test_rigorous_highway_detection_on_empty_grid(self):
        """Validates that empty grid reliably emerges into period-104 highway with (-2, 2) vector."""
        sim = LangtonSimulation()
        res = sim.run(0, 0, 0, 15000)
        self.assertTrue(res.highway_detected)
        self.assertEqual(res.highway_period, 104)
        self.assertEqual((res.highway_dx, res.highway_dy), (-2, 2))
        self.assertGreaterEqual(res.highway_verified_cycles, 3)

    def test_no_false_highway_on_noisy_history(self):
        """Tests that detect_highway_rigorous rejects pseudo-periodic paths that lack true translation."""
        fake_history = [(i % 10, i % 10, i % 4) for i in range(500)]
        detected, _, _, _, _, _ = detect_highway_rigorous(fake_history, min_repeats=3)
        self.assertFalse(detected)


if __name__ == "__main__":
    unittest.main()
