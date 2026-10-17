# Testing & Quality Assurance

This document outlines the testing strategy, test harness structure, and property-based verification mechanisms implemented in `leozaow/leozaow`.

---

## 1. Running the Test Suite

The test suite relies entirely on Python's standard library (`unittest` and `xml.etree.ElementTree`), requiring no external dependencies to execute:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

To run a specific test suite:
```bash
python -m unittest tests.test_stats
python -m unittest tests.test_stats_renderer
python -m unittest tests.test_langton
```

---

## 2. Test Suite Architecture

```
tests/
├── fixtures/
│   └── contributions.json       # Fixed GraphQL contribution calendar payload
├── test_langton.py              # 19 tests: RL rules, infinite plane, SMIL SVG, determinism
├── test_stats.py                # 35 tests: temporal boundaries, streaks, edge cases, reference model
└── test_stats_renderer.py       # 8 tests: XML well-formedness, accessibility, themes, size
```

---

## 3. Coverage Matrix

### 3.1 Statistics Engine (`tests/test_stats.py`)

| Test Case | Scenario Description |
|---|---|
| `test_01_empty_history` | Handles empty dictionary without zero-division or null pointer |
| `test_02_single_contribution_single_day` | Single day activity correctly yields 1-day streak |
| `test_04_zero_contribution_days` | Inactivity between active clusters breaks daily streaks |
| `test_05_current_streak_including_today` | Activity on reference date is correctly counted |
| `test_06_current_streak_ending_yesterday_grace` | Grace period keeps yesterday's streak active when today is 0 |
| `test_07_current_streak_broken_before_yesterday` | Inactivity on today and yesterday returns 0 with null interval |
| `test_09_current_streak_tied_with_record` | Tie-breaker synchronizes current streak with longest streak |
| `test_11_cross_month_streaks` | March 30 to April 3 consecutive run across month boundary |
| `test_12_cross_year_streaks` | December 30 to January 2 run across calendar year boundary |
| `test_13_leap_year_february` | Correct day increment over Feb 29 in leap year (2024) |
| `test_14_non_leap_year_february` | Correct transition from Feb 28 to March 1 in non-leap year (2025) |
| `test_15_iso_week_transitions` | Monday through Sunday ISO boundaries |
| `test_16_week_53` | 53-week years (e.g. 2020) |
| `test_17_unfinished_current_week_grace` | Grace period on unfinished current ISO week |
| `test_18_weekly_vs_daily_semantics` | Weekly streak positive while daily streak is 0 |
| `test_22_future_dated_data` | Future timestamps ignored in current streak determination |
| `test_23_negative_contribution_values` | Strict validation rejects negative counts |
| `test_26_rolling_window_boundaries` | Exact 365-day rolling boundary verification |
| `test_28_streak_longer_than_chart` | 50-day streak highlights all 35 recent chart bars |
| `test_29_grace_period_bar_highlighting` | Grace day (today = 0) is not highlighted in chart |
| `test_34_compare_with_reference_implementation` | Cross-verification against independent simple reference loop |

### 3.2 Visual & Accessibility Engine (`tests/test_stats_renderer.py`)

- **XML Validity**: Strict XML tree parsing for both light and dark themes.
- **Accessibility**: Verifies `<title>`, `<desc>`, `role="img"`, and `aria-label`.
- **Static Readability**: Asserts no `opacity: 0` inline styles exist (preventing invisible text in static rendering).
- **Reduced Motion**: Confirms `@media (prefers-reduced-motion: reduce)` disables entry transitions.
- **Security Check**: Enforces absence of `<script>`, `javascript:`, and credential prefixes (`ghp_`, `gho_`).
- **File Size Threshold**: Enforces `< 25 KiB` for streak cards.

### 3.3 Automaton Engine (`tests/test_langton.py`)

- **Classical RL Rules**: Validates 90° right turns on 0, 90° left turns on 1, and state flipping.
- **Infinite Virtual Plane**: Coordinates crossing the 53×7 calendar bounds execute without modulo wrapping.
- **Deterministic Selection**: Identical contribution calendars yield byte-for-byte identical SVG outputs.
