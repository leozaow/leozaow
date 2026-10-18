# Testing & Quality Assurance

The active statistics system uses Python 3.12 standard-library `unittest` tests and deterministic fixtures.

## 1. Run the Suite

```bash
python -m unittest discover -s tests -p "test_*.py"
```

For individual test modules:

```bash
python -m unittest tests.test_stats
python -m unittest tests.test_stats_renderer
```

Run the end-to-end demo generation and validation:

```bash
python scripts/generate_streak.py --demo --output-dir dist
python scripts/validate_assets.py --dir dist
```

## 2. Coverage

### Contribution and Streak Calculations (`tests/test_stats.py`)

- Empty and single-day histories, gaps between active periods, and counts greater than one.
- Grace-period semantics: today active, today inactive but yesterday active, and genuinely broken streaks.
- Longest streaks, ties, record intervals, and exact date membership.
- Month, year, leap-year, and ISO-week boundaries.
- Malformed dates, negative values, duplicate dates, incomplete API payloads, and deterministic serialization.
- Independent reference calculation for core streak behavior.

### SVG Rendering (`tests/test_stats_renderer.py`)

- Well-formed SVG with dark/light theme tokens.
- Accessible `<title>`, `<desc>`, and readable fallback content.
- No inline invisible initial text, prohibited scripts, or suspicious token prefixes.
- Stable dimensions, dates, bars, and streak highlights.

### Pipeline Smoke Test

`scripts/validate_assets.py` requires only `streak.light.svg`, `streak.dark.svg`, and `stats.json`. It checks XML/JSON structure and basic unsafe-string patterns; it is **not** an exhaustive privacy or security scanner.

## 3. Release Checklist

- Full tests pass with no failures.
- Demo generation produces the three required files.
- Asset validation succeeds.
- README light/dark image references resolve after publication.
- English and Portuguese READMEs have the same intended social links, technical stack, and streak visualization.
- The existing hero assets remain unchanged unless a separate request authorizes a redesign.
- GitHub Actions CI passes; production asset publication is verified separately.
