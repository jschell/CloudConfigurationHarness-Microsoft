# Dependabot Configuration Reference

Two-schedule pattern from jschell/HEIC-convert: daily security, weekly regular.

## `.github/dependabot.yml`

```yaml
version: 2
updates:
  # Security alerts — check daily, keep separate from regular updates
  - package-ecosystem: nuget       # npm | pip | gomod | cargo | etc.
    directory: /
    schedule:
      interval: daily
    open-pull-requests-limit: 5
    labels: [security]

  # Regular updates — weekly, grouped to reduce PR noise
  - package-ecosystem: nuget
    directory: /
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 10
    groups:
      minor-and-patch:
        update-types: [minor, patch]
    labels: [dependencies]

  # Always add GitHub Actions updates too
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

## `.github/workflows/dependabot-auto-merge.yml`

```yaml
name: Dependabot auto-merge

on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    if: github.actor == 'dependabot[bot]'

    steps:
      - uses: actions/checkout@v4

      - name: Get Dependabot metadata
        id: meta
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}

      # Patch / minor — approve and squash merge
      # [bump patch] in commit message triggers the release workflow
      - name: Auto-merge patch and minor
        if: |
          steps.meta.outputs.update-type == 'version-update:semver-patch' ||
          steps.meta.outputs.update-type == 'version-update:semver-minor'
        run: |
          gh pr review "$PR_URL" --approve \
            --body "Auto-approved: ${{ steps.meta.outputs.update-type }}"
          gh pr merge "$PR_URL" --squash \
            --subject "[bump patch] ${{ steps.meta.outputs.dependency-names }}" \
            --auto
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # Major — approve but flag for manual review; never auto-merge
      - name: Flag major for review
        if: steps.meta.outputs.update-type == 'version-update:semver-major'
        run: |
          gh pr review "$PR_URL" --approve \
            --body "Major update — approved but requires manual merge. Check for breaking changes."
          gh pr comment "$PR_URL" \
            --body "**Action required:** This is a major version bump. Please review breaking changes before merging."
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Key decisions

- Security PRs are separate (daily schedule, `security` label) so they can be reviewed and merged faster
- Minor/patch auto-merge uses `[bump patch]` in the squash commit title — this feeds back into the release workflow and produces a patch release automatically
- Major updates are never auto-merged regardless of CI status — breaking changes need a human
- `dependabot/fetch-metadata` is the standard way to read update type; don't parse PR titles manually
