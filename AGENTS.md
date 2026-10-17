# Autonomous Agent Guidelines — `leozaow/leozaow`

Operational directives and governance principles for autonomous AI development agents (ORCA, AGY, Codex, Claude Code, and peer agents) operating within this repository.

---

## 1. Repository Mission & Architecture

The repository serves two primary functions:
1. **Personal Engineering Profile**: The public GitHub profile README for **Leandro Barbosa** (`leozaow`), focused on automation, data engineering, and agentic AI applied to public administration.
2. **Autonomous Self-Hosting Platform**: Automated calculation of GitHub streak statistics and deterministically seeded 2D cellular automata (Langton's Ant) rendered into standalone SVGs.

### Branch Topology
- **`main`**: Production codebase, documentation, tests, static assets, and profile READMEs. Human-authored or agent-verified code commits only. No daily scheduled commits allowed on `main`.
- **`output`**: Asset delivery branch. Automated daily workflows commit generated SVG artifacts (`streak.light.svg`, `streak.dark.svg`, `langton-contribution-graph.svg`, `langton-contribution-graph-dark.svg`, `stats.json`) directly to this branch.

---

## 2. Core Operational Rules

1. **Strict Data Integrity (No Fabrication)**:
   - Agents must never fabricate, guess, or hardcode artificial GitHub contribution counts or streak numbers.
   - Do not generate dummy commits or commit loops to farm streaks or alter contribution graph patterns.
2. **Scope Discipline**:
   - Touch only files directly relevant to the assigned task. Never alter unrelated configuration files or directories.
3. **Safe Branch Publishing**:
   - All automated asset generation commits to `output`.
   - Never force-push (`--force`) to `output` or `main`.
   - Always preserve pre-existing files on `output` (including historical Pac-Man contribution SVGs).
   - Use bounded retries with rebase when pushing to `output`. If push attempts are exhausted, the workflow must fail with a nonzero exit code.
4. **Security & Privacy**:
   - Never commit or log personal access tokens, credentials, private server IPs, or confidential workplace information.
   - SVGs must contain zero `<script>` tags, zero `javascript:` handlers, and no external font/asset dependencies.
5. **Accessibility & Static Readability**:
   - SVGs must render fully in static contexts (e.g. reader mode, image proxies, mobile).
   - Elements must NOT use `opacity: 0` as an initial inline style.
   - Always include descriptive `<title>` and `<desc>` elements in SVGs, and provide appropriate alt text in Markdown images.
   - Respect `@media (prefers-reduced-motion: reduce)`.

---

## 3. Coding Standards & Tech Stack

- **Python Baseline**: Python 3.12 standard library (`dataclasses`, `datetime`, `urllib`, `json`, `xml.etree.ElementTree`).
- **Dependencies**: Zero unnecessary third-party packages. Rely on stdlib unless explicitly justified.
- **Pure Functions**: Isolate business logic into pure, deterministic functions (`scripts/stats/calculations.py`, `scripts/langton_sim.py`).
- **Typing**: Use static type annotations (`from __future__ import annotations`, `typing`).

---

## 4. Verification & Testing Requirements

Before concluding any task or pushing changes:
1. Run the full test suite:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
2. Verify asset generation and validation:
   ```bash
   python scripts/generate_streak.py --demo --output-dir dist
   python scripts/generate_langton.py --input tests/fixtures/contributions.json --output-dir dist
   python scripts/validate_assets.py --dir dist
   ```
3. Ensure all tests pass with zero failures and zero errors.

---

## 5. Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <imperative description in lowercase>
```

- **Types**:
  - `feat`: New capability, badge, or automation feature
  - `fix`: Bug fix, broken link, or rendering correction
  - `docs`: Documentation updates (`README.md`, `docs/`, `AGENTS.md`)
  - `refactor`: Structural code cleanup with no behavior change
  - `test`: Adding or updating test cases
  - `ci`: Changes to GitHub Actions workflows
  - `chore`: Routine dependency updates or maintenance
