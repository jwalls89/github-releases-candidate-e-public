# Manual Test Plan: Release Pipeline Workflows

This plan covers the three primary workflows (Cut Release, Tag RC, Hotfix) plus edge cases. All tests should be run via the GitHub Actions **workflow_dispatch** UI.

## Prerequisites

- A clean repo state on `main` with at least one commit
- No in-flight releases (no `release/X.Y.Z` branch without a matching `vX.Y.Z` tag)
- Access to trigger workflows manually (Actions tab)

---

## 1. Cut Release (cut-release.yml)

### 1.1 Happy path — first release
- [ ] Trigger **Cut Release Candidate** with version `1.0.0`
- [ ] Verify `release/1.0.0` branch created on origin
- [ ] Verify `v1.0.0-rc.1` tag created on origin
- [ ] Verify pre-release `v1.0.0-rc.1` visible on Releases page
- [ ] Verify Promote workflow was triggered (check Actions tab)
- [ ] Verify step summary contains branch, tag, and commit SHA

### 1.2 Happy path — subsequent release
- [ ] Finalise `1.0.0` first (or use a repo with an existing stable release)
- [ ] Trigger **Cut Release Candidate** with version `2.0.0`
- [ ] Verify version is accepted (higher than latest stable)
- [ ] Verify branch, tag, and pre-release created as above

### 1.3 Edge case — version not higher than latest
- [ ] Trigger **Cut Release Candidate** with a version equal to or lower than the latest stable tag
- [ ] Verify workflow fails with a clear error message

### 1.4 Edge case — release already in-flight
- [ ] With an existing `release/X.Y.Z` branch that has no final `vX.Y.Z` tag
- [ ] Trigger **Cut Release Candidate** with a new version
- [ ] Verify workflow fails with "still in-flight" error

### 1.5 Edge case — v prefix in input
- [ ] Trigger **Cut Release Candidate** with version `v1.0.0` (with v prefix)
- [ ] Verify the `v` prefix is stripped and the workflow succeeds

### 1.6 Edge case — invalid version format
- [ ] Trigger **Cut Release Candidate** with version `1.0` or `abc`
- [ ] Verify workflow fails with a validation error

---

## 2. Tag RC (tag-rc.yml)

### 2.1 Happy path — tag second RC
- [ ] Have an existing `release/X.Y.Z` branch with `vX.Y.Z-rc.1` already tagged
- [ ] Push a fix commit to `release/X.Y.Z`
- [ ] Trigger **Tag New RC** with the version (e.g., `1.0.0`)
- [ ] Verify `vX.Y.Z-rc.2` tag created (auto-incremented)
- [ ] Verify pre-release `vX.Y.Z-rc.2` visible on Releases page
- [ ] Verify Promote workflow was triggered
- [ ] Verify step summary shows correct tag, branch, and commit

### 2.2 Happy path — tag first RC on existing branch
- [ ] Have a `release/X.Y.Z` branch with no RC tags
- [ ] Trigger **Tag New RC** with the version
- [ ] Verify `vX.Y.Z-rc.1` is created

### 2.3 Edge case — non-sequential RC numbers
- [ ] Manually delete an RC tag (e.g., delete rc.2 but rc.1 and rc.3 exist)
- [ ] Trigger **Tag New RC**
- [ ] Verify it creates rc.4 (next after highest, not gap-filling)

### 2.4 Edge case — release already finalised
- [ ] Have a version where `vX.Y.Z` stable tag already exists
- [ ] Trigger **Tag New RC** with that version
- [ ] Verify workflow fails with "already finalised" error

### 2.5 Edge case — release branch does not exist
- [ ] Trigger **Tag New RC** with a version that has no `release/` branch
- [ ] Verify workflow fails with "branch does not exist" error

### 2.6 Edge case — v prefix in input
- [ ] Trigger **Tag New RC** with version `v1.0.0`
- [ ] Verify the `v` prefix is stripped and the workflow succeeds

---

## 3. Hotfix (hotfix.yml)

### 3.1 Happy path — first hotfix
- [ ] Have a finalised release with stable tag `v1.0.0`
- [ ] Trigger **Hotfix** with base version `1.0.0`
- [ ] Verify `release/1.0.1` branch created on origin
- [ ] Verify branch was created from the `v1.0.0` tag commit (not main HEAD)
- [ ] Verify step summary shows correct base version, hotfix version, and commit

### 3.2 Happy path — second hotfix on same minor
- [ ] Have `v1.0.0` finalised and `release/1.0.1` already exists (or `v1.0.1` tag exists)
- [ ] Trigger **Hotfix** with base version `1.0.0`
- [ ] Verify it creates `release/1.0.2` (skips used patch numbers)

### 3.3 Edge case — RC tags count as used patches
- [ ] Have `v1.0.0` finalised and a `v1.0.1-rc.1` tag (no stable `v1.0.1`)
- [ ] Trigger **Hotfix** with base version `1.0.0`
- [ ] Verify it creates `release/1.0.2` (skips 1.0.1 since RC exists)

### 3.4 Edge case — base tag does not exist
- [ ] Trigger **Hotfix** with a version that has no stable tag
- [ ] Verify workflow fails with "does not exist" error

### 3.5 Edge case — hotfix branch already exists
- [ ] Have `release/1.0.1` already created
- [ ] Trigger **Hotfix** with base version `1.0.0` (where next patch would be `1.0.1`)
- [ ] Verify workflow fails with "already exists" error

### 3.6 Edge case — v prefix in input
- [ ] Trigger **Hotfix** with base version `v1.0.0`
- [ ] Verify the `v` prefix is stripped and the workflow succeeds

### 3.7 Edge case — hotfix version skips multiple patches
- [ ] Have `v1.0.0` finalised, `v1.0.1` finalised, `v1.0.2-rc.1` tagged
- [ ] Trigger **Hotfix** with base version `1.0.0`
- [ ] Verify it creates `release/1.0.3`

---

## 4. Full Pipeline (end-to-end)

### 4.1 Cut through to finalise
- [ ] Cut release `3.0.0` (creates branch + rc.1 + triggers promote)
- [ ] Approve promote through test, preprod, prod
- [ ] Verify finalise creates `v3.0.0` stable tag and release
- [ ] Verify Releases page shows `v3.0.0` as Latest

### 4.2 Fix and re-promote
- [ ] After cutting `3.0.0`, push a fix to `release/3.0.0`
- [ ] Tag new RC (should be rc.2)
- [ ] Verify previous promote run is cancelled (concurrency group)
- [ ] Approve new promote through to finalise
- [ ] Verify final release includes the fix

### 4.3 Hotfix after finalise
- [ ] After `3.0.0` is finalised, trigger Hotfix with base `3.0.0`
- [ ] Push a fix to the hotfix branch
- [ ] Tag RC on the hotfix branch
- [ ] Promote through to finalise
- [ ] Verify merge-back issue is created if hotfix branch has unique commits
