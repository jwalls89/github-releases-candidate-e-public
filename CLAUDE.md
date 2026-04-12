# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A reference implementation of **Candidate E** — a release management workflow system built entirely on GitHub Actions. It implements trunk-based development with release branches, using GitHub's Releases page as the single source of truth for deployment state (pre-releases show RC promotion history, stable releases show what's in production).

There is no application code, build system, or test suite. The entire project is GitHub Actions workflows, environment config files, and documentation.

## Repository Layout

- `.github/workflows/` — The five workflow files that implement the release pipeline
- `environments/` — Per-environment JSON config (`test.json`, `preprod.json`, `prod.json`) with container versions
- `VERSION` — Current version number
- `README.md` — Comprehensive usage guide with scenarios and state diagrams

## Workflow Architecture

The release pipeline flows: **Cut → Promote → Finalise**, with an optional **Tag RC** loop for fixes.

```
cut-release.yml ──→ promote.yml (test → preprod → prod → finalise)
                         ↑
tag-rc.yml ──────────────┘  (re-enters promotion after fixes)

hotfix.yml ──→ creates isolated patch branch from a stable tag
```

### Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `cut-release.yml` | Manual dispatch | Creates `release/X.Y.0` branch + `vX.Y.0-rc.1` tag + pre-release, then triggers promote |
| `promote.yml` | Triggered by cut-release or tag-rc | Deploys RC through test→preprod→prod with approval gates, then finalises (creates stable tag + release, detects merge-back needs) |
| `tag-rc.yml` | Manual dispatch from release branch | Auto-increments RC number, creates new pre-release, restarts promotion pipeline |
| `hotfix.yml` | Manual dispatch from main | Creates `release/X.Y.Z` (Z>0) branch from a stable tag for isolated fixes |
| `deploy.yml` | Called by promote.yml (reusable) | Reads environment config and simulates deployment to a single environment |

### Key Design Decisions

- **Concurrency**: `cut-release` uses a single group to prevent simultaneous cuts. `promote` uses `cancel-in-progress: true` so re-tagging an RC restarts the pipeline.
- **Changelog accuracy**: `promote.yml` finds the previous stable release via `gh release list --exclude-drafts --exclude-pre-releases` and passes it as `previous_tag_name` so the final changelog shows all changes since the last stable release, not just since the RC.
- **RC auto-increment**: `tag-rc.yml` uses `git ls-remote --tags` to find the highest existing RC number and increments by 1.
- **Merge-back detection**: After finalising, the pipeline counts commits on the release branch not on main (`git rev-list --count`). If any exist, it annotates the release and creates a GitHub issue with merge-back instructions.
- **Version validation**: All workflows validate semver format (`^[0-9]+\.[0-9]+\.[0-9]+$`) and guard against duplicate releases, missing branches, and already-finalised versions.

## Working With This Repo

Since this is a workflow-only repository, development means editing YAML workflows and testing them by running the GitHub Actions manually (workflow_dispatch). There are no local build, lint, or test commands.

To validate workflow syntax locally, use `actionlint` if available:
```
actionlint .github/workflows/*.yml
```

Environment promotion requires GitHub Environment protection rules configured on the repository (preprod and prod need required reviewers). See the README "Setup" section for configuration steps.
