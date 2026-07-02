# Branch Protection Reference

Set these up immediately — before merging any code.

## `gh` CLI (one-shot setup)

```bash
OWNER=<owner>
REPO=<repo>

gh api "repos/$OWNER/$REPO/branches/main/protection" \
  --method PUT \
  --header "Accept: application/vnd.github+json" \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[contexts][]=build" \
  -f "enforce_admins=true" \
  -f "required_pull_request_reviews[required_approving_review_count]=1" \
  -f "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -f "required_conversation_resolution=true" \
  -f "allow_force_pushes=false" \
  -f "allow_deletions=false" \
  -F "restrictions=null"
```

Replace `build` with the exact job name from your CI workflow's `jobs:` key.

## Checklist

- [ ] Require CI status check passing (`build` job)
- [ ] Require branch to be up to date before merging (`strict: true`)
- [ ] Enforce for administrators (no bypass)
- [ ] Require at least 1 approving review
- [ ] Dismiss stale reviews when new commits are pushed
- [ ] Require conversation resolution
- [ ] Prevent force pushes to main
- [ ] Prevent branch deletion

## Why enforce for admins

Skipping admin enforcement is the most common way rules get quietly bypassed during incidents. The cost of an extra PR is lower than the cost of broken main.
