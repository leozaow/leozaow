# Operations & Automation Guide

This guide covers routine operational workflows, manual execution, troubleshooting, and asset management for `leozaow/leozaow`.

---

## 1. Local Execution & Development

### 1.1 Generating Streak Cards Locally

**Demo Mode (Deterministic Mock Data)**:
```bash
python scripts/generate_streak.py --demo --output-dir dist
```
Generates `streak.light.svg`, `streak.dark.svg`, and `stats.json` in `dist/`.

**Production Mode (Live GitHub GraphQL API)**:
```bash
GITHUB_TOKEN=$(gh auth token) python scripts/generate_streak.py --output-dir dist
```

**Custom Reference Date (Testing Historical Dates)**:
```bash
python scripts/generate_streak.py --demo --reference-date 2026-10-17 --output-dir dist
```

### 1.2 Generating Langton's Ant Contribution Graph

**Fixture Mode**:
```bash
python scripts/generate_langton.py --input tests/fixtures/contributions.json --output-dir dist
```

**Live API Mode**:
```bash
GITHUB_TOKEN=$(gh auth token) GITHUB_REPOSITORY_OWNER=leozaow python scripts/generate_langton.py --output-dir dist
```

### 1.3 Validating Generated Assets

```bash
python scripts/validate_assets.py --dir dist
```
Validates:
- XML well-formedness for all SVG files
- Maximum file size (< 350 KiB)
- Security checks (no embedded `<script>`, `javascript:`, or token prefixes)
- JSON schema completeness for `stats.json`

---

## 2. GitHub Actions Workflow Operations

Asset generation is automated via `.github/workflows/profile-assets.yml`.

### 2.1 Triggering Manual Generation (workflow_dispatch)

Via GitHub CLI:
```bash
gh workflow run profile-assets.yml
```

Via Web Interface:
1. Navigate to **Actions** -> **Generate and publish profile assets**.
2. Click **Run workflow** -> Select `main` branch -> Click **Run workflow**.

### 2.2 Publication Protocol

1. The workflow checks out `main` and runs the unit test suite (`python -m unittest discover tests`).
2. Both generators emit assets into `dist/`.
3. `validate_assets.py` inspects the staged files.
4. The workflow fetches `origin/output` into an isolated Git worktree (`../output-worktree`).
5. Only `streak.light.svg`, `streak.dark.svg`, `stats.json`, `langton-contribution-graph.svg`, and `langton-contribution-graph-dark.svg` are copied.
6. Existing files on `output` (including historical `pacman-*.svg` assets) are strictly preserved.
7. If staged changes exist, a commit is created and pushed with a 5-attempt exponential backoff rebase loop.
8. If all push attempts fail, the workflow exits with code 1.

---

## 3. Rollback Procedures

### 3.1 Reverting to Previous Streak or Langton Assets
To revert an asset on the `output` branch without affecting `main`:
```bash
git fetch origin output
git checkout output
git checkout HEAD~1 -- langton-contribution-graph.svg langton-contribution-graph-dark.svg
git commit -m "chore(rollback): restore previous Langton SVGs"
git push origin output
git checkout main
```

### 3.2 Activating Historical Pac-Man Rollback
The `output` branch retains `pacman-contribution-graph.svg` and `pacman-contribution-graph-dark.svg`. If desired, update the image URLs in `README.md` to point back to the Pac-Man artifacts.
