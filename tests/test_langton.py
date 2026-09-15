"""Comprehensive test suite for Langton's Ant × GitHub Contributions engine."""

import copy
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.langton_sim import (
    DIRECTIONS,
    DIR_NAMES,
    CalendarCell,
    CalendarData,
    LangtonSimulation,
    detect_highway,
    get_candidate_origins,
    parse_contribution_calendar,
    score_trajectory,
    seed_grid_from_calendar,
    select_best_simulation,
)
from scripts.langton_render import render_langton_svg
from scripts.generate_langton import generate_all

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contributions.json"


class TestLangtonEngine(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            self.fixture_data = json.load(f)
        self.calendar = parse_contribution_calendar(self.fixture_data)

    def test_rl_rule_classic_small_steps(self):
        """Tests that the RL rule behaves exactly as defined:
        0 (white): turn right, flip to 1, move forward.
        1 (black): turn left, flip to 0, move forward.
        """
        # Starting on completely empty grid at (0, 0) facing North (direction=0)
        sim = LangtonSimulation()
        res = sim.run(start_x=0, start_y=0, start_dir=0, max_steps=4)

        # Step 0: at (0, 0), state is 0.
        # Should turn Right (dir 1: East), flip (0,0) -> 1, move to (1, 0)
        self.assertEqual(res.steps[0].x, 0)
        self.assertEqual(res.steps[0].y, 0)
        self.assertEqual(res.steps[0].cell_state_before, 0)
        self.assertEqual(sim.get_state(0, 0), 1)

        # Step 1: at (1, 0), state is 0.
        # Facing East (dir 1), turns Right (dir 2: South), flips (1,0) -> 1, moves to (1, 1)
        self.assertEqual(res.steps[1].x, 1)
        self.assertEqual(res.steps[1].y, 0)
        self.assertEqual(res.steps[1].cell_state_before, 0)
        self.assertEqual(sim.get_state(1, 0), 1)

        # Step 2: at (1, 1), state is 0.
        # Facing South (dir 2), turns Right (dir 3: West), flips (1,1) -> 1, moves to (0, 1)
        self.assertEqual(res.steps[2].x, 1)
        self.assertEqual(res.steps[2].y, 1)
        self.assertEqual(sim.get_state(1, 1), 1)

        # Step 3: at (0, 1), state is 0.
        # Facing West (dir 3), turns Right (dir 0: North), flips (0,1) -> 1, moves to (0, 0)
        self.assertEqual(res.steps[3].x, 0)
        self.assertEqual(res.steps[3].y, 1)
        self.assertEqual(sim.get_state(0, 1), 1)

        # Now test hitting a black cell (state 1):
        # The next move will enter (0, 0), which is currently 1!
        sim2 = LangtonSimulation({(0, 0): 1})
        res2 = sim2.run(start_x=0, start_y=0, start_dir=0, max_steps=1)
        # At (0, 0), state is 1 -> Turn Left (dir 0 -> dir 3: West), flip to 0, advance to (-1, 0)
        self.assertEqual(res2.steps[0].cell_state_before, 1)
        self.assertEqual(sim2.get_state(0, 0), 0)

    def test_infinite_sparse_plane_negative_coords_no_wrap(self):
        """Tests that moving outside (0..52, 0..6) works smoothly without wrap-around."""
        sim = LangtonSimulation()
        # Move ant intentionally to negative coordinates
        res = sim.run(start_x=0, start_y=0, start_dir=3, max_steps=10)
        # Ant moves into x < 0 or y < 0
        min_x = min(s.x for s in res.steps)
        min_y = min(s.y for s in res.steps)
        self.assertTrue(min_x < 0 or min_y < 0, "Ant should freely explore negative coordinates without wrapping.")

    def test_calendar_mapping_preservation(self):
        """Verifies weeks, days, dates and counts are correctly mapped into CalendarData."""
        self.assertGreaterEqual(self.calendar.weeks_count, 52)
        self.assertEqual(self.calendar.total_contributions, 229)
        # Verify specific known active cells from fixture
        active_cells = [c for c in self.calendar.cells.values() if c.count > 0]
        self.assertEqual(len(active_cells), 36)
        total_sum = sum(c.count for c in active_cells)
        self.assertEqual(total_sum, 229)

    def test_seed_grid_from_contributions(self):
        """Checks rule: count > 0 becomes state 1; count == 0 is state 0."""
        grid = seed_grid_from_calendar(self.calendar)
        for (x, y), cell in self.calendar.cells.items():
            if cell.count > 0:
                self.assertEqual(grid.get((x, y)), 1)
            else:
                self.assertNotIn((x, y), grid)

    def test_deterministic_selection(self):
        """Verifies candidate selection and best simulation scoring are 100% deterministic."""
        res1 = select_best_simulation(self.calendar, steps_count=180)
        res2 = select_best_simulation(self.calendar, steps_count=180)

        self.assertEqual(res1.start_x, res2.start_x)
        self.assertEqual(res1.start_y, res2.start_y)
        self.assertEqual(res1.start_dir, res2.start_dir)
        self.assertEqual(len(res1.steps), len(res2.steps))
        for s1, s2 in zip(res1.steps, res2.steps):
            self.assertEqual((s1.x, s1.y, s1.direction), (s2.x, s2.y, s2.direction))

    def test_deterministic_byte_for_byte_svg_generation(self):
        """Ensures two independent renders of the same fixture produce bitwise identical SVGs."""
        best = select_best_simulation(self.calendar, steps_count=180)
        svg1 = render_langton_svg(self.calendar, best, theme="light")
        svg2 = render_langton_svg(self.calendar, best, theme="light")
        self.assertEqual(hashlib.sha256(svg1.encode("utf-8")).hexdigest(), hashlib.sha256(svg2.encode("utf-8")).hexdigest())

        svg_dark1 = render_langton_svg(self.calendar, best, theme="dark")
        svg_dark2 = render_langton_svg(self.calendar, best, theme="dark")
        self.assertEqual(hashlib.sha256(svg_dark1.encode("utf-8")).hexdigest(), hashlib.sha256(svg_dark2.encode("utf-8")).hexdigest())

    def test_svg_xml_validity_and_safety(self):
        """Tests that both light and dark SVGs parse as valid XML, contain required elements,
        and strictly forbid <script>, external links or token leakages.
        """
        best = select_best_simulation(self.calendar, steps_count=180)
        for theme in ["light", "dark"]:
            svg = render_langton_svg(self.calendar, best, theme=theme)
            # 1. XML parse
            root = ET.fromstring(svg)
            self.assertEqual(root.tag.split("}")[-1], "svg")

            # 2. Required title and desc
            titles = [el.text for el in root.iter() if el.tag.endswith("title")]
            descs = [el.text for el in root.iter() if el.tag.endswith("desc")]
            self.assertTrue(len(titles) >= 1)
            self.assertTrue(len(descs) >= 1)

            # 3. Security: No scripts
            self.assertNotIn("<script", svg.lower())
            self.assertNotIn("javascript:", svg.lower())
            self.assertNotIn("gho_", svg)
            self.assertNotIn("ghp_", svg)
            self.assertNotIn("token", svg.lower())

    def test_reasonable_svg_size(self):
        """Checks that generated SVGs do not exceed reasonable size thresholds (< 200 KB, spec asks < 350 KB)."""
        best = select_best_simulation(self.calendar, steps_count=180)
        svg_light = render_langton_svg(self.calendar, best, theme="light")
        svg_dark = render_langton_svg(self.calendar, best, theme="dark")

        size_light = len(svg_light.encode("utf-8"))
        size_dark = len(svg_dark.encode("utf-8"))

        self.assertLess(size_light, 200 * 1024, f"Light SVG is too large: {size_light} bytes")
        self.assertLess(size_dark, 200 * 1024, f"Dark SVG is too large: {size_dark} bytes")

    def test_sparse_or_empty_calendar_handling(self):
        """Tests simulation and rendering on a completely empty calendar (0 commits)."""
        empty_cal = CalendarData(
            total_contributions=0,
            weeks_count=53,
            cells={(w, d): CalendarCell(w, d, f"2026-01-{d+1:02d}", 0, "NONE") for w in range(53) for d in range(7)},
            min_date="2025-01-01",
            max_date="2026-01-01",
        )
        best = select_best_simulation(empty_cal, steps_count=180)
        self.assertIsNotNone(best)
        svg = render_langton_svg(empty_cal, best, theme="dark")
        self.assertIn("0 CONTRIBUIÇÕES", svg)
        ET.fromstring(svg)

    def test_highway_detector(self):
        """Tests that the highway detector correctly identifies a period-104 translational highway."""
        sim = LangtonSimulation()
        res = sim.run(0, 0, 0, 10500)
        self.assertTrue(res.highway_detected)
        self.assertEqual(res.highway_period, 104)


if __name__ == "__main__":
    unittest.main()
