"""Smoke tests for GitHub profile content and local asset references."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READMES = ("README.md", "README.pt-BR.md")


def core_stack(text: str) -> str:
    start = text.index("### Core Technical Stack")
    end = text.index("\n---\n", start)
    return text[start:end].strip()


class TestProfileContent(unittest.TestCase):
    def test_local_image_assets_exist(self) -> None:
        for filename in READMES:
            with self.subTest(readme=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                for source in re.findall(r'(?:src|srcset)="(\./[^"]+)"', text):
                    relpath = source.split("?", 1)[0].removeprefix("./")
                    self.assertTrue((ROOT / relpath).is_file(), f"{filename}: missing {relpath}")

    def test_english_and_portuguese_stack_match(self) -> None:
        en = (ROOT / READMES[0]).read_text(encoding="utf-8")
        pt = (ROOT / READMES[1]).read_text(encoding="utf-8")
        self.assertEqual(core_stack(en), core_stack(pt))

    def test_core_visual_assets_and_social_links(self) -> None:
        urls = ("linkedin.com/in/leozaow", "lattes.cnpq.br", "instagram.com/leozaow_",
                "youtube.com/leozaow", "x.com/leozaow", "facebook.com/Leozaow",
                "twitch.tv/leozaow")
        for filename in READMES:
            with self.subTest(readme=filename):
                text = (ROOT / filename).read_text(encoding="utf-8")
                self.assertIn("./assets/hero-dark.svg", text)
                self.assertIn("./assets/hero-light.svg", text)
                self.assertIn("streak.dark.svg", text)
                self.assertIn("streak.light.svg", text)
                self.assertIn("nous-girl.png", text)
                self.assertNotIn("Langton", text)
                for url in urls:
                    self.assertIn(url, text)

    def test_active_workflows_do_not_generate_retired_visuals(self) -> None:
        for relpath in (".github/workflows/profile-assets.yml",
                        ".github/workflows/validation.yml", "scripts/validate_assets.py"):
            with self.subTest(file=relpath):
                text = (ROOT / relpath).read_text(encoding="utf-8").lower()
                self.assertNotIn("langton", text)


if __name__ == "__main__":
    unittest.main()
