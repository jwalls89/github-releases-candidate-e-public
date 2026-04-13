# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A reference implementation of **Candidate E** — a release management workflow system built on GitHub Actions + Python. It implements trunk-based development with release branches, using GitHub's Releases page as the single source of truth for deployment state (pre-releases show RC promotion history, stable releases show what's in production).

The repo has two layers: GitHub Actions workflows (YAML) that orchestrate the pipeline, and a Python package (`release_tools`) that implements the core release logic called by those workflows via invoke tasks.

## Development Commands

The project uses `uv` for Python dependency management. All commands run through `uv run`:

```bash
# Install dependencies
uv sync

# Lint
uv run ruff check src/ tasks/ tests/
uv run ruff format --check src/ tasks/ tests/

# Type check
uv run ty check src/ tasks/

# Unit tests
uv run pytest tests/unit/

# Run a single test file
uv run pytest tests/unit/release_tools/test_cut_release.py

# Validate workflow YAML syntax
uv run actionlint .github/workflows/*.yml

# Run the cut-release task locally (requires .env with GH_TOKEN)
uv run invoke release.cut-release --version 1.2.0
```

Pre-commit hooks run automatically on commit (ruff, actionlint, gitleaks, etc.). The `no-commit-to-branch` hook blocks direct commits to `main`.

## Repository Layout

- `src/release_tools/` — Python package implementing release logic (version parsing, git operations, GitHub API calls)
- `tasks/` — Invoke task definitions that wire up the Python classes for CLI/CI use
- `tests/unit/` — Unit tests (pytest) for the `release_tools` package
- `.github/workflows/` — Seven workflow files implementing the release pipeline and CI
- `.github/actions/` — Composite actions: `setup-python` (uv + deps) and `code-quality` (ruff + ty + pytest)
- `environments/` — Per-environment JSON config (`test.json`, `preprod.json`, `prod.json`) with container versions
- `VERSION` — Current version number

## Code Architecture

### Python Package (`src/release_tools/`)

The `cut-release.yml` workflow delegates to Python via `uv run invoke release.cut-release`. The Python code is structured as:

- `CutRelease` — orchestrator: parses version, validates it's higher than latest, checks no release is in-flight, then creates branch + tag + pre-release + triggers promote
- `GitHelper` — wraps `gitpython` for branch/tag operations and querying release state (latest stable tag, in-flight releases)
- `GitHubHelper` — wraps `PyGithub` for creating pre-releases and triggering the promote workflow
- `ReleaseVersionHelper` — semver parsing/validation using the `semver` library
- `GitHubActionsHelper` — detects CI vs local execution (controls where `GH_TOKEN` comes from)

The invoke task in `tasks/release.py` wires these together: on GitHub Actions it reads `GH_TOKEN` and `GITHUB_REPOSITORY` from the environment; locally it loads from `.env` and derives the repo name from the git remote.

### Workflow Architecture

The release pipeline flows: **Cut → Promote → Finalise**, with an optional **Tag RC** loop for fixes.

```
cut-release.yml ──→ promote.yml (test → preprod → prod → finalise)
                         ↑
tag-rc.yml ──────────────┘  (re-enters promotion after fixes)

hotfix.yml ──→ creates isolated patch branch from a stable tag
```

| Workflow | Trigger | Purpose |
|---|---|---|
| `cut-release.yml` | Manual dispatch | Calls Python to create `release/X.Y.0` branch + `vX.Y.0-rc.1` tag + pre-release, then triggers promote |
| `promote.yml` | Triggered by cut-release or tag-rc | Deploys RC through test→preprod→prod with approval gates, then finalises (creates stable tag + release, detects merge-back needs) |
| `tag-rc.yml` | Manual dispatch from release branch | Auto-increments RC number, creates new pre-release, restarts promotion pipeline |
| `hotfix.yml` | Manual dispatch from main | Creates `release/X.Y.Z` (Z>0) branch from a stable tag for isolated fixes |
| `deploy.yml` | Called by promote.yml (reusable) | Reads environment config and simulates deployment to a single environment |
| `main.yml` | Push to main | Runs code quality checks (ruff, ty, pytest) |
| `pr.yml` | Pull requests | Runs the same code quality checks as main |

### Key Design Decisions

- **Concurrency**: `cut-release` uses a single group to prevent simultaneous cuts. `promote` uses `cancel-in-progress: true` so re-tagging an RC restarts the pipeline.
- **Changelog accuracy**: `promote.yml` finds the previous stable release via `gh release list --exclude-drafts --exclude-pre-releases` and passes it as `previous_tag_name` so the final changelog shows all changes since the last stable release, not just since the RC.
- **RC auto-increment**: `tag-rc.yml` uses `git ls-remote --tags` to find the highest existing RC number and increments by 1.
- **Merge-back detection**: After finalising, the pipeline counts commits on the release branch not on main (`git rev-list --count`). If any exist, it annotates the release and creates a GitHub issue with merge-back instructions.
- **Version validation**: All workflows validate semver format (`^[0-9]+\.[0-9]+\.[0-9]+$`) and guard against duplicate releases, missing branches, and already-finalised versions.
- **In-flight guard**: `CutRelease` checks for existing release branches without a matching final tag and blocks concurrent releases.
- **Ruff config**: `ALL` rules enabled with specific ignores; `T201` (print) allowed since print is used intentionally for workflow output.
