# Autonomous Agent Guidelines — `leozaow/leozaow`

This repository contains a **personal technology experimentation profile** and a small, automated GitHub contribution analytics system. It is not a claim of professional software engineering seniority or an official Public Administration project.

## 1. Editorial Contract

- Present the author as a technology enthusiast and experimenter who learns by building independent projects.
- Public Administration is professional background, **not** the subject or owner of these personal experiments.
- Do not imply that the author's personal tools are official public-sector systems.
- The English `README.md` is the primary profile; `README.pt-BR.md` is its faithful Portuguese companion.
- Preserve the existing hero SVG artwork unless explicitly asked to alter it.
- Preserve the **Core Technical Stack** categories and icon selection unless expressly requested.
- The statistics and streak card remains English-language in both README versions.
- List tools used or explored without presenting icon lists as professional certifications or proficiency ratings.
- Do not publish confidential employment information, internal system identifiers, private project configuration, server addresses, or credentials.
- Avoid invented statistics, accolades, project outcomes, and marketing language.

## 2. Repository Boundaries

- `main`: README files, hero and badge assets, scripts, tests, workflows, and internal technical documentation.
- `output`: automatically published `streak.light.svg`, `streak.dark.svg`, and `stats.json`; older unrelated assets may remain as historical artifacts.
- The active visualization is **GitHub contribution/streak analytics**. Do not re-enable retired visualizations without an explicit request.
- Do not modify unrelated repositories or external infrastructure.
- Do not force-push either branch.

## 3. Engineering Standards

- Use Python 3.12 and its standard library unless a dependency is justified.
- Separate GitHub data retrieval, normalization, computation, SVG rendering, and publication.
- Use deterministic reference dates in tests; no artificial GitHub activity or cosmetic streak inflation.
- Distinguish GitHub contributions from Git commits and missing data from zero contributions.
- Keep renderings usable in static SVG viewers, readable in light/dark modes, and accessible to screen readers.
- Avoid scripts, external fonts, credential strings, and essential animated-only text in generated SVGs.
- GitHub Actions publication must fail if it cannot publish required assets.

## 4. Validation Before Release

```bash
python -m unittest discover -s tests -p "test_*.py"
python scripts/generate_streak.py --demo --output-dir dist
python scripts/validate_assets.py --dir dist
```

Review local README image paths, technical claims, README language parity, and both hero references. Inspect actual GitHub rendering and workflow outcomes when available. A green test run is not proof of successful remote publication.

## 5. Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) with focused changes:
`feat`, `fix`, `docs`, `refactor`, `test`, `ci`, or `chore`. Include verification details in the handoff; do not claim unperformed tests or deployment.
