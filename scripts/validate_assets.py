#!/usr/bin/env python3
"""Asset validation script for generated SVG and JSON artifacts.

Verifies XML well-formedness, required elements, SVG namespaces, size limits,
and absence of credentials or script tags.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_FILES = [
    "streak.light.svg",
    "streak.dark.svg",
    "stats.json",
]

MAX_SVG_BYTES = 350 * 1024  # 350 KiB


def validate_svg(path: Path) -> None:
    content = path.read_bytes()
    if len(content) > MAX_SVG_BYTES:
        raise ValueError(f"File {path.name} exceeds max size: {len(content)} bytes > {MAX_SVG_BYTES}")

    text = content.decode("utf-8")
    lower = text.lower()

    if "<script" in lower:
        raise ValueError(f"Security error: <script> found in {path.name}")
    if "javascript:" in lower:
        raise ValueError(f"Security error: javascript: URL found in {path.name}")
    for token_prefix in ("ghp_", "gho_", "github_pat_"):
        if token_prefix in text:
            raise ValueError(f"Security error: potential token {token_prefix} in {path.name}")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"XML parse error in {path.name}: {e}") from e

    if not root.tag.endswith("svg"):
        raise ValueError(f"Root element in {path.name} is not <svg>: {root.tag}")


def validate_json(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in {path.name}: {e}") from e

    required_keys = ["current_streak", "longest_streak", "contributions_last_year", "recent_activity_days"]
    for k in required_keys:
        if k not in data:
            raise ValueError(f"Missing key '{k}' in {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated profile assets.")
    parser.add_argument(
        "--dir",
        type=Path,
        required=True,
        help="Directory containing the generated assets to validate.",
    )
    args = parser.parse_args()

    target_dir: Path = args.dir
    if not target_dir.is_dir():
        print(f"Error: directory does not exist: {target_dir}", file=sys.stderr)
        return 1

    errors = []
    for filename in REQUIRED_FILES:
        filepath = target_dir / filename
        if not filepath.exists():
            errors.append(f"Missing required asset: {filename}")
            continue

        try:
            if filename.endswith(".svg"):
                validate_svg(filepath)
            elif filename.endswith(".json"):
                validate_json(filepath)
            print(f"[OK] Validated {filename} ({filepath.stat().st_size:,} bytes)")
        except Exception as e:
            errors.append(f"Validation failed for {filename}: {e}")

    if errors:
        print("\nAsset validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  [FAIL] {err}", file=sys.stderr)
        return 1

    print("\nAll assets passed validation successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
