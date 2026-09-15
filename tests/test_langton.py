"""Comprehensive test suite for Langton's Ant × GitHub Contributions engine (V2)."""

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
    seed_grid_from_calendar,
    select_best_simulation,
)
from scripts.langton_analysis import analyze_deep_simulation, score_deep_candidate
from scripts.langton_render import render_langton_svg_v2
from scripts.generate_langton import generate_all

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contributions.json"


class TestLangtonEngineV2(unittest.TestCase):
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

        # Step 0: at (0, 0), state 0, facing North (0)
        s0 = res.steps[0]
        self.assertEqual(s0.x, 0)
        self.assertEqual(s0.y, 0)
        self.assertEqual(s0.direction_before, 0)
        self.assertEqual(s0.turn_direction, "R")
        self.assertEqual(s0.direction_after, 1)  # Facing East
        self.assertEqual(s0.cell_state_before, 0)
        self.assertEqual(s0.cell_state_after, 1)
        self.assertEqual(sim.get_state(0, 0), 1)

        # Step 1: at (1, 0), state 0, facing East (1)
        s1 = res.steps[1]
        self.assertEqual(s1.x, 1)
        self.assertEqual(s1.y, 0)
        self.assertEqual(s1.direction_before, 1)
        self.assertEqual(s1.turn_direction, "R")
        self.assertEqual(s1.direction_after, 2)  # Facing South
        self.assertEqual(s1.cell_state_before, 0)
        self.assertEqual(s1.cell_state_after, 1)

        # Step 2: at (1, 1), state 0, facing South (2)
        s2 = res.steps[2]
        self.assertEqual(s2.direction_after, 3)  # Facing West

        # Step 3: at (0, 1), state 0, facing West (3)
        s3 = res.steps[3]
        self.assertEqual(s3.direction_after, 0)  # Facing North (heading back to 0,0)

        # Step 4: next step visits (0, 0) which is currently 1
        res2 = sim.run(start_x=0, start_y=0, start_dir=0, max_steps=1)
        s4 = res2.steps[0]
        self.assertEqual(s4.cell_state_before, 1)
        self.assertEqual(s4.turn_direction, "L")
        self.assertEqual(s4.direction_after, 3)  # Turns Left to West
        self.assertEqual(s4.cell_state_after, 0)
        self.assertEqual(sim.get_state(0, 0), 0)

    def test_infinite_sparse_plane_negative_coords_no_wrap(self):
        """Tests that moving outside calendar bounds operates smoothly on an infinite plane."""
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

    def test_deterministic_selection_and_scoring(self):
        """Verifies candidate selection and scoring are 100% deterministic."""
        sim1, a1 = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)
        sim2, a2 = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)

        self.assertEqual(sim1.start_x, sim2.start_x)
        self.assertEqual(sim1.start_y, sim2.start_y)
        self.assertEqual(sim1.start_dir, sim2.start_dir)
        self.assertEqual(len(sim1.steps), len(sim2.steps))
        for s1, s2 in zip(sim1.steps, sim2.steps):
            self.assertEqual((s1.x, s1.y, s1.direction_after), (s2.x, s2.y, s2.direction_after))

    def test_deterministic_byte_for_byte_svg_v2(self):
        """Ensures two independent renders of the same fixture produce bitwise identical SVGs."""
        sim, analysis = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)
        svg1 = render_langton_svg_v2(self.calendar, sim, analysis, theme="light")
        svg2 = render_langton_svg_v2(self.calendar, sim, analysis, theme="light")
        self.assertEqual(hashlib.sha256(svg1.encode("utf-8")).hexdigest(), hashlib.sha256(svg2.encode("utf-8")).hexdigest())

        svg_dark1 = render_langton_svg_v2(self.calendar, sim, analysis, theme="dark")
        svg_dark2 = render_langton_svg_v2(self.calendar, sim, analysis, theme="dark")
        self.assertEqual(hashlib.sha256(svg_dark1.encode("utf-8")).hexdigest(), hashlib.sha256(svg_dark2.encode("utf-8")).hexdigest())

    def test_svg_xml_validity_and_security(self):
        """Tests that both light and dark SVGs parse as valid XML, contain required elements,
        and strictly forbid <script>, external links or token leakages.
        """
        sim, analysis = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)
        for theme in ["light", "dark"]:
            svg = render_langton_svg_v2(self.calendar, sim, analysis, theme=theme)
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

    def test_progressive_trail_and_dynamic_overlays_presence(self):
        """Verifies that the trail animates via stroke-dashoffset (not pre-drawn)
        and that automaton-state-layer overlays are generated for flipped cells.
        """
        sim, analysis = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)
        svg = render_langton_svg_v2(self.calendar, sim, analysis, theme="dark")

        # Trail dashoffset animation
        self.assertIn("stroke-dasharray:", svg)
        self.assertIn("animation: trail-reveal", svg)
        self.assertIn("@keyframes trail-reveal", svg)

        # Dual-layer presence
        self.assertIn('id="calendar-data-layer"', svg)
        self.assertIn('id="automaton-state-layer"', svg)
        self.assertIn('class="state-overlay', svg)

        # Agent micro-ant with antennae
        self.assertIn('class="ant-antenna"', svg)
        self.assertIn('class="ant-eye"', svg)

    def test_svg_size_under_limit(self):
        """Checks that generated SVGs do not exceed 250 KiB (spec allows up to 350 KiB)."""
        sim, analysis = select_best_simulation(self.calendar, steps_count=240, deep_horizon=5000)
        svg_light = render_langton_svg_v2(self.calendar, sim, analysis, theme="light")
        svg_dark = render_langton_svg_v2(self.calendar, sim, analysis, theme="dark")

        self.assertLess(len(svg_light.encode("utf-8")), 250 * 1024)
        self.assertLess(len(svg_dark.encode("utf-8")), 250 * 1024)

    def test_empty_or_sparse_calendar_handling(self):
        """Tests simulation and rendering on an empty calendar."""
        empty_cal = CalendarData(
            total_contributions=0,
            weeks_count=53,
            cells={(w, d): CalendarCell(w, d, f"2026-01-{d+1:02d}", 0, "NONE") for w in range(53) for d in range(7)},
            min_date="2025-01-01",
            max_date="2026-01-01",
        )
        sim, analysis = select_best_simulation(empty_cal, steps_count=240, deep_horizon=2000)
        self.assertIsNotNone(sim)
        svg = render_langton_svg_v2(empty_cal, sim, analysis, theme="dark")
        self.assertIn("0 CONTRIBUIÇÕES", svg)
        ET.fromstring(svg)

    def test_highway_emergence_validation(self):
        """Validates that empty grid reliably emerges into period-104 highway."""
        sim = LangtonSimulation()
        res = sim.run(0, 0, 0, 10500)
        self.assertTrue(res.highway_detected)
        self.assertEqual(res.highway_period, 104)


if __name__ == "__main__":
    unittest.main()
