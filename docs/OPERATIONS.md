# Operations & Automation Guide

This guide covers the active GitHub contribution and streak analytics pipeline in `leozaow/leozaow`.

## 1. Local Generation

Requires Python 3.12.

Create deterministic demonstration assets:

```bash
python scripts/generate_streak.py --demo --output-dir dist
python scripts/validate_assets.py --dir dist
```

Specify a fixed date when diagnosing date-dependent behavior:

```bash
python scripts/generate_streak.py --demo --reference-date 2026-10-17 --output-dir dist
```

Generate with live GitHub GraphQL data, providing a token with the required read access:

```bash
GITHUB_TOKEN="$(gh auth token)" GITHUB_REPOSITORY_OWNER=leozaow python scripts/generate_streak.py --output-dir dist
python scripts/validate_assets.py --dir dist
```

The output directory contains `streak.light.svg`, `streak.dark.svg`, and `stats.json`. The validator checks required files, XML validity, size, common script-injection strings, and the presence of required JSON keys.

## 2. GitHub Actions

- `validation.yml` checks the unit tests and deterministic demonstration generation on pull requests and relevant pushes.
- `profile-assets.yml` runs on its configured schedule, on relevant code changes to `main`, or via manual dispatch. It runs tests, retrieves live contribution data, generates assets, validates them, and publishes the required files to `output`.
- Schedule execution is best effort; it is not guaranteed to occur at an exact minute.

To trigger manually:

```bash
gh workflow run profile-assets.yml
```

The GitHub website also exposes **Actions → Generate and publish profile assets → Run workflow**.

## 3. Publication Behavior

1. Workflows run the unit tests before writing production assets.
2. Only required analytics artifacts are staged for publication.
3. The publisher uses an isolated worktree for the `output` branch.
4. No content changes means no new asset commit.
5. A rejected push triggers bounded retry attempts; exhausted attempts fail the job.
6. Other existing assets on `output` are not rewritten or removed during routine generation.
7. Job summaries and remote workflow results must be checked before claiming successful publication.

## 4. Recovering and Rolling Back

If an asset is broken, review the failing run, `stats.json`, and the latest `output` commits. Fix generation on `main` and rerun the workflow whenever practical.

To restore a previously published artifact version without rewriting history, check out `output` and restore the desired prior revision of only these files:

```bash
git fetch origin
git switch output
git restore --source=HEAD~1 -- streak.light.svg streak.dark.svg stats.json
git add streak.light.svg streak.dark.svg stats.json
git commit -m "fix(assets): restore prior validated streak output"
git push origin output
```

Select the correct historical revision rather than assuming `HEAD~1` is always the right recovery target. Do not force-push `main` or `output`.

## 5. Common Checks

- Missing/invalid `GITHUB_TOKEN`: inspect job permissions and GraphQL response.
- Missing or inconsistent dates: inspect input coverage and [Metrics Methodology](METRICS_METHODOLOGY.md).
- Asset verification failure: inspect the validator error; do not bypass checks to publish.
- Push conflicts: inspect output-branch history and rerun after resolving the genuine conflict.
- Stale image in README: verify the `output` branch and rendered GitHub image URL before blaming the generator.
