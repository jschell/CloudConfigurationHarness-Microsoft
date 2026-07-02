---
name: gh-release
description: Use when setting up GitHub Actions for CI, versioned releases, and Dependabot — scaffolds workflows from a proven pattern with commit-keyword versioning
allowed-tools: Bash
---

# GitHub Release Workflows

Wire up CI, releases, and Dependabot in five phases. Reference implementation: jschell/HEIC-convert.

## Phase 1 — Inventory

Ask before writing any YAML:

| Question | Default |
|----------|---------|
| Stack / runtime? | detect from repo |
| Build + test command? | (required) |
| Artifact type? | binary / package / none |
| Publish target? | GitHub Releases only |
| Runner OS? | ubuntu-latest (windows-latest for .NET WPF/WinForms) |

## Phase 2 — CI workflow (`.github/workflows/ci.yml`)

Triggers on PRs to `main`. Gate merges on this passing.

Key jobs in order:
1. **restore** — cache dependencies (see references/ci-workflow.md for cache key patterns)
2. **build** — compile or lint
3. **vulnerability-scan** — `continue-on-error: true` *(deliberate design decision — surfaces CVEs without blocking mid-PR)*
4. **test** — run twice: once for results XML, once for coverage
5. **smoke-test** — launch artifact, wait 5 s, assert still running

Always set `timeout-minutes: 15` on every job.

## Phase 3 — Release workflow (`.github/workflows/release.yml`)

Triggers on push to `main` when commit message contains a keyword:

| Keyword | Effect |
|---------|--------|
| `[release]` | publish current version unchanged |
| `[bump patch]` | 0.1.2 → 0.1.3 |
| `[bump minor]` | 0.1.2 → 0.2.0 |
| `[bump major]` | 0.1.2 → 1.0.0 |

**Use `RELEASE_TOKEN` (PAT), not `GITHUB_TOKEN`** — `GITHUB_TOKEN` triggers are blocked by GitHub's anti-loop protection and the release event will be swallowed silently. *(deliberate design decision)*

Job sequence: `check-release` → `build-and-release` → `publish-<target>` (continue-on-error).

Always generate a SHA256 checksum alongside each artifact. See references/release-workflow.md for full template.

Start at `v0.1.0`, not `v1.0.0` — reserve `1.0.0` for production-stable.

## Phase 4 — Dependabot (`.github/dependabot.yml` + `.github/workflows/dependabot-auto-merge.yml`)

**dependabot.yml** — two separate schedules:
- Security alerts: `daily`
- Regular updates: `weekly`, group minor+patch together

**dependabot-auto-merge.yml** — differentiated by update type:
- patch / minor → auto-approve + squash merge with `[bump patch]` tag (feeds back into release workflow)
- major → auto-approve + comment requesting manual review, do NOT merge

Use `gh` CLI for approvals and merges. Requires `contents: write` and `pull-requests: write` permissions.

See references/dependabot-config.md for full templates.

## Phase 5 — Branch protection

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["build"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

Checklist:
- [ ] Require CI passing before merge
- [ ] Enforce for administrators
- [ ] Prevent force pushes to main
- [ ] Require conversation resolution

## Gotchas (from HEIC-convert lessons learned)

| Gotcha | Fix |
|--------|-----|
| Release event never fires | Use `RELEASE_TOKEN` PAT; `GITHUB_TOKEN` is silently blocked |
| Cache fails with no lock file | Manual `actions/cache@v4` with `hashFiles('**/*.csproj')` or equivalent |
| Single-file publish breaks WPF/WinForms | Disable trimming; add `IncludeNativeLibrariesForSelfExtract=true` |
| Native DLLs won't load from memory | Same fix above — required for WPF `wpfgfx_cor3.dll` |
| Started versioning at v1.0.0 | Use `0.1.0` until stable |
| Merging PRs without CI | Accumulates technical debt fast; enforce branch protection day one |
| Major dep update auto-merged | Never auto-merge major; breaking changes require human review |

## Integration

- Before this → use `repo-init` skill to create the repo structure and CI stub
- `repo-init` creates a minimal CI stub; this skill replaces and extends it
