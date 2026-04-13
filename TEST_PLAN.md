# Manual Test Plan: Release Pipeline Workflows

Tests are ordered so each builds on the state left by the previous one.
All tests run via GitHub Actions **workflow_dispatch** UI or `gh workflow run`.

## Prerequisites

- A clean repo state on `main` with at least one commit
- No tags, releases, or release branches
- Access to trigger workflows manually (Actions tab)

---

## Phase 1: Cut Release — first release + edge cases needing in-flight state

### 1.1 Cut Release — happy path (first release, v1.0.0)
- [x] Trigger **Cut Release Candidate** with version `1.0.0` (run 24337567767)
- [x] Verify `release/1.0.0` branch created on origin (`52c6d5b`)
- [x] Verify `v1.0.0-rc.1` tag created on origin (`52c6d5b`)
- [x] Verify pre-release `v1.0.0-rc.1` visible on Releases page
- [x] Verify Promote workflow was triggered (run 24337578852)
- [x] Verify step summary contains branch, tag, and commit SHA (visible in logs)

> State after: `release/1.0.0` exists, `v1.0.0-rc.1` tagged, no stable tag — release is in-flight.

### 1.2 Cut Release — release already in-flight
- [x] Trigger **Cut Release Candidate** with version `3.0.0` (run 24338066056)
- [x] Verify workflow fails with "still in-flight" error ("Release 1.0.0 is still in-flight")

### 1.3 Cut Release — invalid version format
- [x] Trigger **Cut Release Candidate** with version `abc` (run 24338109713)
- [x] Verify workflow fails with a validation error ("Version must be in semver format")

### 1.4 Cut Release — v prefix in input
> Cannot test independently — v prefix on `v1.0.0` would hit the in-flight guard.
> Tested later in Tag RC and Hotfix v-prefix tests instead.

---

## Phase 2: Promote v1.0.0 to stable

### 2.1 Promote — approve through to finalise
- [x] Approve promote pipeline through test, preprod, prod environments (run 24337578852)
- [x] Verify finalise creates `v1.0.0` stable tag (`ba9dd20`)
- [x] Verify stable release `v1.0.0` visible on Releases page as Latest
- [x] Verify step summary visible in logs ("## Release Finalised")

> State after: `v1.0.0` finalised. `release/1.0.0` branch still exists.

---

## Phase 3: Tag RC — tests on the finalised v1.0.0 branch

### 3.1 Tag RC — release already finalised
- [x] Trigger **Tag New RC** with version `1.0.0` (run 24338289686)
- [x] Verify workflow fails with "already finalised" error ("Release v1.0.0 is already finalised")

### 3.2 Tag RC — release branch does not exist
- [x] Trigger **Tag New RC** with version `9.9.9` (run 24338350441)
- [x] Verify workflow fails (checkout step fails — branch doesn't exist on origin; Python validation is redundant on CI but useful locally)

---

## Phase 4: Cut Release — subsequent release + remaining edge cases

### 4.1 Cut Release — happy path (subsequent release, v2.0.0)
- [x] Trigger **Cut Release Candidate** with version `2.0.0` (run 24339171623)
- [x] Verify version is accepted (higher than stable v1.0.0)
- [x] Verify `release/2.0.0` branch, `v2.0.0-rc.1` tag, and pre-release created (`52c6d5b`)
- [x] Verify Promote workflow was triggered (run 24339181969)
- [x] Verify step summary visible in logs

> State after: `release/2.0.0` in-flight, `v1.0.0` finalised.

### 4.2 Cut Release — version not higher than latest
- [x] Trigger **Cut Release Candidate** with version `0.5.0` (run 24339290842)
- [x] Verify workflow fails with a clear error message ("Version 0.5.0 is not higher than the latest release 1.0.0")

---

## Phase 5: Tag RC — tests on the in-flight v2.0.0 branch

### 5.1 Tag RC — happy path (second RC)
- [x] Push a fix commit to `release/2.0.0` (VERSION bump, `ca1e323`)
- [x] Trigger **Tag New RC** with version `2.0.0` (run 24339469708)
- [x] Verify `v2.0.0-rc.2` tag created (auto-incremented, `ca1e323`)
- [x] Verify pre-release `v2.0.0-rc.2` visible on Releases page
- [x] Verify Promote workflow was triggered (run 24339479206)
- [x] Verify step summary shows correct tag, branch, and commit

### 5.2 Tag RC — v prefix in input
- [x] Trigger **Tag New RC** with version `v2.0.0` (run 24343298348)
- [x] Verify the `v` prefix is stripped and `v2.0.0-rc.3` is created

### 5.3 Tag RC — non-sequential RC numbers
- [x] Delete `v2.0.0-rc.2` tag from origin (rc.1 and rc.3 remain)
- [x] Trigger **Tag New RC** with version `2.0.0` (run 24344960394)
- [x] Verify it creates `v2.0.0-rc.4` (next after highest, not gap-filling)

---

## Phase 6: Promote v2.0.0 to stable

### 6.1 Promote — approve through to finalise
- [x] Approve promote pipeline through test, preprod, prod (run 24345746228)
- [x] Verify `v2.0.0` stable tag and release created (`bcdd93`, via GitHub API)
- [x] Verify Releases page shows `v2.0.0` as Latest

> State after: `v1.0.0` and `v2.0.0` both finalised.

---

## Phase 7: Hotfix

### 7.1 Hotfix — base tag does not exist
- [x] Trigger **Hotfix** with base version `9.9.9` (run 24346136573)
- [x] Verify workflow fails (checkout step fails — tag doesn't exist on origin; Python validation is backup for local use)

### 7.2 Hotfix — happy path (first hotfix on v1.0.0)
- [x] Trigger **Hotfix** with base version `1.0.0` (run 24346240049)
- [x] Verify `release/1.0.1` branch created on origin (`52c6d5b`)
- [x] Verify branch was created from the `v1.0.0` tag commit (`52c6d5b`, not main HEAD)
- [x] Verify step summary shows correct base version, hotfix version, and commit

### 7.3 Hotfix — v prefix in input
- [x] Trigger **Hotfix** with base version `v2.0.0` (run 24346480600)
- [x] Verify the `v` prefix is stripped and `release/2.0.1` is created (`ca1e323`)

### 7.4 Hotfix — skips existing branches
- [x] Trigger **Hotfix** with base version `1.0.0` (run 24349437604, release/1.0.1 exists)
- [x] Verify workflow skips to `release/1.0.2` (`52c6d5b`, branched from v1.0.0 tag commit)

### 7.5 Hotfix — RC tags and branches count as used patches
- [x] Tag RC on `release/1.0.1` (created `v1.0.1-rc.1`, run 24349569168)
- [x] Trigger **Hotfix** with base version `1.0.0` (run 24349626215)
- [x] Verify it creates `release/1.0.3` (skips 1.0.1 RC tag + 1.0.2 branch)

### 7.6 Hotfix — skips multiple used patches
- [ ] Finalise `v1.0.1` (promote through to stable)
- [ ] Trigger **Hotfix** with base version `1.0.0`
- [ ] Verify it creates `release/1.0.3` (skips 1.0.1 finalised and 1.0.2 with branch)

---

## Phase 8: Full end-to-end scenarios

### 8.1 Fix and re-promote (v3.0.0)
- [x] Cut release 3.0.0 (run 24350541023), pushed fix to `release/3.0.0` (`fffb0cd`)
- [x] Tag new RC → `v3.0.0-rc.2` at fix commit (run 24350694095)
- [x] Verify previous promote run cancelled (24350556746 → cancelled)
- [x] Approve new promote through to finalise (run 24350711657)
- [x] Verify final release `v3.0.0` points to fix commit (`fffb0cd`)

### 8.2 Hotfix through to finalise with merge-back (v3.0.1)
- [x] Trigger Hotfix on v3.0.0 → created `release/3.0.1` (run 24351223003)
- [x] Push fix to hotfix branch (`2551738`)
- [x] Tag RC → `v3.0.1-rc.1` (run 24351404470)
- [x] Promote through to finalise (run 24351423624)
- [x] Verify merge-back issue created: "Merge back: v3.0.1" (issue #14)
