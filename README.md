# Candidate E: Trunk-Based + Release Branches + GitHub Releases Dashboard

Same branching model as Candidate B, but uses GitHub Releases (pre-release → stable) as the single source of truth for release state.

## How It Differs from Candidate B

The branching model, promotion flow, and all guardrails are identical to Candidate B. The difference is visibility:

| What you want to know | Candidate B | Candidate E |
|----------------------|-------------|-------------|
| What's being promoted? | Look at RC tags | **Pre-releases** on Releases page |
| What's in prod? | Find the latest final tag | **Latest stable release** on Releases page |
| How many attempts? | Count RC tags | Count **pre-releases** on Releases page |
| Full changelog | Click the GitHub Release | Click the GitHub Release — notes show ALL changes since last stable release |

The Releases page becomes the dashboard. Anyone can glance at it and know the state of the world.

## How It Works

### Releases Page States

```
Releases page after a clean release:

  v1.2.0         [Latest]       Stable release — this is in prod
  v1.2.0-rc.1   [Pre-release]  The candidate that made it through

Releases page during a bumpy promotion:

  v1.3.0-rc.3   [Pre-release]  Third attempt — currently promoting
  v1.3.0-rc.2   [Pre-release]  Second attempt — had a config issue
  v1.3.0-rc.1   [Pre-release]  First attempt — failed in test
  v1.2.0         [Latest]       Still the current prod release

After v1.3.0 reaches prod:

  v1.3.0         [Latest]       Stable — changelog shows ALL changes since v1.2.0
  v1.3.0-rc.3   [Pre-release]  The RC that made it
  v1.3.0-rc.2   [Pre-release]  Second attempt
  v1.3.0-rc.1   [Pre-release]  First attempt
  v1.2.0                        Previous prod release
```

### Pipeline Flow

```
 ┌───────────────────────┐   ┌──────────────────────────────────────────────────────┐
 │  Cut Release Candidate │   │              Promote (auto-triggered)                │
 │  (from main)           │   │                                                      │
 │                        │   │  ┌──────┐  ┌─────────┐  ┌──────┐  ┌──────────────┐ │
 │ Creates:          triggers │  │ Test │─►│ Preprod  │─►│ Prod │─►│ Finalise     │ │
 │ - branch          ────────►│  │(auto)│  │(approval)│  │(approval)│- final tag  │ │
 │ - rc.1 tag             │   │  └──────┘  └─────────┘  └──────┘  │- stable      │ │
 │ - pre-release          │   │                                     │  release     │ │
 └───────────────────────┘   │                                     │- merge-back  │ │
                              │                                     │  issue       │ │
 ┌───────────────────────┐   │                                     └──────────────┘ │
 │  Tag New RC            │   │                                                      │
 │  (from release/*)  triggers  (pipeline restarts, cancels previous run)            │
 │                   ────────►│                                                      │
 │ Creates:               │   └──────────────────────────────────────────────────────┘
 │ - rc.N tag             │
 │ - pre-release          │
 └───────────────────────┘

 ┌───────────────────────┐
 │  Hotfix                │  Creates a new release/X.Y.Z branch from a release tag.
 │  (from main)           │  Then: push fix → Tag New RC → same pipeline as above.
 └───────────────────────┘
```

## Key Concepts

| Concept | What it means |
|---------|---------------|
| **main** | Where all development happens. Never stops. |
| **release/X.Y.0** | Cut from main when ready to release. Lives ~1 week during promotion. |
| **release/X.Y.Z** (Z>0) | Hotfix branch, cut from a release tag. Isolated from the original. |
| **Pre-release** | Published for each RC tag. Shows promotion history on the Releases page. |
| **Stable release** | Published when an RC reaches prod. Changelog shows ALL changes since previous stable release. |
| **Merge-back issue** | Created automatically at finalise if the release branch has fixes not on main. |

## Environments

| Environment | Gate | Who approves |
|-------------|------|-------------|
| test | Automatic | Nobody — deploys immediately |
| preprod | Required reviewer | Configured in repo settings |
| prod | Required reviewer | Configured in repo settings |

## Workflows

| Workflow | Run from branch | Trigger | Purpose |
|----------|----------------|---------|---------|
| **Cut Release Candidate** | `main` | Manual | Creates branch + rc.1 tag + pre-release, triggers Promote |
| **Tag New RC** | `release/*` | Manual | Creates next RC tag + pre-release after a fix, triggers Promote |
| **Hotfix** | `main` | Manual | Creates a new patch release branch from a release tag |
| **Promote** | `release/*` | Auto-triggered | Deploys test → preprod → prod, creates stable release at prod |
| **Deploy** | `release/*` | Called by Promote | Simulates deployment to one environment |

---

## Setup

Before running scenarios, configure GitHub Environments:

1. Go to **Settings → Environments**
2. Create environment `test` — no protection rules needed
3. Create environment `preprod`:
   - Tick **Required reviewers**
   - Add yourself (or your team)
   - Click **Save protection rules**
4. Create environment `prod`:
   - Tick **Required reviewers**
   - Add yourself (or your team)
   - Click **Save protection rules**

---

## Scenario 1: Happy Path

A clean release — no fixes needed, straight through to prod.

### Step 1: Cut the release candidate

1. Go to **Actions → Cut Release Candidate → Run workflow**
2. Enter version: `1.2.0`
3. Click **Run workflow**

This creates:
- Branch `release/1.2.0`
- Tag `v1.2.0-rc.1`
- **Pre-release** `v1.2.0-rc.1` on the Releases page

### Step 2: Watch it flow

The Promote workflow triggers automatically:
1. **Test** — deploys automatically
2. **Preprod** — click **Review deployments** → approve
3. **Prod** — click **Review deployments** → approve
4. **Finalise** — creates tag `v1.2.0` and a **stable release** with full changelog since the previous release

### Step 3: Verify

- **Releases** page → `v1.2.0` is **Latest** with full changelog
- Pre-release `v1.2.0-rc.1` shows the single RC that made it through

---

## Scenario 2: Unpolished Path

Release hits problems during promotion. Fix, re-tag, restart.

### Step 1: Cut and start promotion

1. **Cut Release Candidate** with version `1.3.0`
2. Promote triggers automatically, deploys to test
3. Something is wrong — do NOT approve preprod

**Releases page now shows:**
- `v1.3.0-rc.1` [Pre-release] — first attempt
- `v1.2.0` [Latest] — still the current prod release

### Step 2: Fix the issue on the release branch

```bash
git checkout release/1.3.0
git pull origin release/1.3.0
# Make the fix
git add environments/test.json
git commit -m "fix: correct api endpoint in test config"
git push origin release/1.3.0
```

### Step 3: Tag a new RC and restart promotion

1. Go to **Actions → Tag New RC**
2. In the branch dropdown, **select `release/1.3.0`** (not main)
3. Enter version: `1.3.0`
4. Click **Run workflow**

**Releases page now shows:**
- `v1.3.0-rc.2` [Pre-release] — new attempt with fix
- `v1.3.0-rc.1` [Pre-release] — previous failed attempt
- `v1.2.0` [Latest] — still the current prod release

### Step 4: Approve through environments

Eventually an RC makes it through. The finalise step creates a **stable release** `v1.3.0`.

**Releases page now shows:**
- `v1.3.0` [Latest] — stable release, changelog shows ALL changes since v1.2.0
- `v1.3.0-rc.2` [Pre-release] — the RC that made it
- `v1.3.0-rc.1` [Pre-release] — the first attempt that failed
- `v1.2.0` — previous prod release

### Step 5: Merge back

The finalise step creates a **merge-back issue** with instructions. Follow them.

---

## Scenario 3: Hotfix

Production has a critical issue. Main has moved on. Fix what's in prod without pulling in new features.

### Step 1: Create a hotfix branch

1. Go to **Actions → Hotfix → Run workflow**
2. Enter base version: `1.3.0` (the version currently in prod)
3. Click **Run workflow**

This creates `release/1.3.1` branched from the `v1.3.0` tag.

### Step 2: Push your fix

```bash
git fetch origin
git checkout release/1.3.1
# Make the fix
git add .
git commit -m "fix: increase auth timeout to prevent 504s"
git push origin release/1.3.1
```

### Step 3: Start promotion

1. Go to **Actions → Tag New RC**
2. In the branch dropdown, **select `release/1.3.1`** (not main)
3. Enter version: `1.3.1`
4. Click **Run workflow**

**Releases page now shows:**
- `v1.3.1-rc.1` [Pre-release] — hotfix in progress
- `v1.3.0` [Latest] — still the current prod release

### Step 4: Approve through all environments

Same flow: test (auto) → preprod (approve) → prod (approve) → finalise.

**Releases page now shows:**
- `v1.3.1` [Latest] — hotfix in prod, changelog shows changes since v1.3.0
- `v1.3.1-rc.1` [Pre-release] — the hotfix RC
- `v1.3.0` — previous prod release

### Step 5: Merge back

The finalise step creates a **merge-back issue**. Follow the instructions.

---

## Merge-Back Process

When a release has fixes not on main (scenarios 2 and 3), the finalise step:
1. Annotates the stable release with a merge-back notice
2. Creates an issue with step-by-step instructions

```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b merge-back/1.3.0
git merge origin/release/1.3.0
# Resolve conflicts if any
git push origin merge-back/1.3.0
```

Then open a PR from `merge-back/1.3.0` to `main`, review, and merge. Close the issue once done.

---

## Quick Reference

| Action | How |
|--------|-----|
| Cut a release candidate | Actions → **Cut Release Candidate** (from main) → enter version |
| Approve promotion | Click paused workflow run → **Review deployments** → approve |
| Fix during promotion | Push fix to release branch → Actions → **Tag New RC** (from release branch) → enter version |
| Start a hotfix | Actions → **Hotfix** (from main) → enter base version currently in prod |
| Promote a hotfix | Push fix to hotfix branch → Actions → **Tag New RC** (from hotfix branch) → enter version |
| Merge back fixes | Follow the merge-back issue created by finalise |
| See what's in prod | **Releases** page → **Latest** stable release |
| See what's in-flight | **Releases** page → **Pre-releases** without a matching stable release |
| See promotion history | **Releases** page → trail of pre-releases for each version |
| See full changelog | Click any stable release → notes show ALL changes since previous stable release |

## Branching Rules

| Branch | Who commits here | Deploys to |
|--------|-----------------|------------|
| `main` | Everyone (via PRs) | dev |
| `release/X.Y.0` | Fixes only during promotion | test → preprod → prod |
| `release/X.Y.Z` (Z>0) | Hotfix only | test → preprod → prod |
| `feature/*` | Developer working on a feature | ephemeral (via PR) |
