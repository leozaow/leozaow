"""Unit tests for the streak SVG renderer.

Verifies XML well-formedness, accessibility tags, absence of scripts/secrets,
theme fidelity, reduced motion handling, and file size limits.
"""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from scripts.stats.calculations import calculate_streak_stats
from scripts.stats.renderer import THEMES, render_streak_svg


class TestStatsRenderer(unittest.TestCase):
    """Verifies SVG rendering quality, accessibility, and conformance."""

    def setUp(self):
        self.ref_date = date(2026, 10, 17)
        # Create a realistic test calendar
        days = {
            self.ref_date - timedelta(days=i): (1 + (i % 5))
            for i in range(1, 18)
        }
        days[self.ref_date] = 0  # test grace period
        self.stats = calculate_streak_stats(
            days=days,
            reference_date=self.ref_date,
            username="leozaow",
        )

    def test_xml_well_formedness_light_and_dark(self):
        """Verifies both light and dark SVGs parse as valid XML."""
        for theme in ("light", "dark"):
            svg = render_streak_svg(self.stats, theme=theme)
            try:
                root = ET.fromstring(svg)
            except ET.ParseError as e:
                self.fail(f"SVG for theme '{theme}' failed to parse as XML: {e}")
            self.assertEqual(root.tag.split("}")[-1], "svg")

    def test_accessibility_elements_present(self):
        """Verifies title, desc, role, and aria-label are present and non-empty."""
        svg = render_streak_svg(self.stats, theme="dark")
        root = ET.fromstring(svg)
        title_elem = root.find("{http://www.w3.org/2000/svg}title")
        desc_elem = root.find("{http://www.w3.org/2000/svg}desc")

        self.assertIsNotNone(title_elem)
        self.assertIsNotNone(desc_elem)
        self.assertIn("leozaow", title_elem.text or "")
        self.assertIn("Current streak", desc_elem.text or "")
        self.assertEqual(root.attrib.get("role"), "img")
        self.assertIn("aria-label", root.attrib)

    def test_static_readability_no_zero_initial_opacity(self):
        """Verifies text elements do NOT have initial opacity 0 (zero-opacity bug fix)."""
        svg = render_streak_svg(self.stats, theme="dark")
        # Text elements should never have inline opacity: 0
        self.assertNotIn('style="opacity: 0', svg)
        self.assertNotIn("opacity: 0;", svg)

    def test_reduced_motion_media_query_present(self):
        """Verifies prefers-reduced-motion media query is included."""
        svg = render_streak_svg(self.stats, theme="dark")
        self.assertIn("@media (prefers-reduced-motion: reduce)", svg)
        self.assertIn("animation: none !important;", svg)

    def test_no_embedded_scripts_or_secrets(self):
        """Verifies SVG is clean of <script>, javascript:, tokens, or sensitive patterns."""
        for theme in ("light", "dark"):
            svg = render_streak_svg(self.stats, theme=theme)
            self.assertNotIn("<script", svg.lower())
            self.assertNotIn("javascript:", svg.lower())
            self.assertNotIn("ghp_", svg)
            self.assertNotIn("gho_", svg)
            self.assertNotIn("bearer", svg.lower())

    def test_file_size_limit(self):
        """Verifies SVG card output is lightweight (under 25 KiB)."""
        for theme in ("light", "dark"):
            svg = render_streak_svg(self.stats, theme=theme)
            size_kb = len(svg.encode("utf-8")) / 1024.0
            self.assertLess(size_kb, 25.0, f"SVG size {size_kb:.1f} KiB exceeds 25 KiB threshold")

    def test_theme_color_tokens(self):
        """Verifies theme background and accent colors match visual identity."""
        dark_svg = render_streak_svg(self.stats, theme="dark")
        light_svg = render_streak_svg(self.stats, theme="light")

        self.assertIn(THEMES["dark"]["bg"], dark_svg)
        self.assertIn(THEMES["dark"]["border"], dark_svg)
        self.assertIn(THEMES["light"]["bg"], light_svg)
        self.assertIn(THEMES["light"]["border"], light_svg)

    def test_bar_chart_series_count_and_highlight(self):
        """Verifies 35 bars are rendered and current streak dates are correctly highlighted."""
        svg = render_streak_svg(self.stats, theme="dark")
        root = ET.fromstring(svg)
        # Find all 35 bar rect elements inside the chart (which have a <title> element)
        bars = [r for r in root.findall(".//{http://www.w3.org/2000/svg}rect") if r.find("{http://www.w3.org/2000/svg}title") is not None]
        self.assertEqual(len(bars), 35)

        # Verify that yesterday's bar (Oct 16) has streak color and today's bar (Oct 17) does not
        orange = THEMES["dark"]["bar_streak"]
        inactive = THEMES["dark"]["bar_inactive"]

        today_bar = bars[-1]
        yesterday_bar = bars[-2]
        self.assertEqual(today_bar.attrib.get("fill"), inactive)
        self.assertEqual(yesterday_bar.attrib.get("fill"), orange)


if __name__ == "__main__":
    unittest.main()
