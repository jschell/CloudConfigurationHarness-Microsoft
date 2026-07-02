---
name: finishing-a-development-branch
description: Use when implementation is complete and all tests pass - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options.

**Core principle:** Verify tests → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests

```bash
npm test  # or project-appropriate command
```

**If tests fail:** Stop. Don't proceed until fixed.

**If tests pass:** Continue to Step 2.

### Step 2: Determine Base Branch

```bash
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

### Step 3: Present Options

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

### Step 4: Execute Choice

**Option 1: Merge Locally**
```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
# Verify tests
git branch -d <feature-branch>
```

**Option 2: Push and Create PR/MR**
```bash
git push -u origin <feature-branch>
```

Detect platform and create PR/MR:
```bash
remote=$(git remote get-url origin 2>/dev/null)
case "$remote" in
  *github.com*)    gh pr create --title "..." --body "..." ;;
  *gitlab.com*)    glab mr create --title "..." --description "..." ;;
  *bitbucket*)     echo "Create PR via Bitbucket web UI" ;;
  *dev.azure.com*) az repos pr create --title "..." ;;
  *)               echo "Unknown platform - use web UI" ;;
esac
```

Override with `GIT_PLATFORM` env var if needed.

| Platform | CLI |
|----------|-----|
| GitHub | `gh` |
| GitLab | `glab` |
| Azure DevOps | `az repos` |

**Option 3: Keep As-Is**
Report location, don't cleanup.

**Option 4: Discard**
Require typed "discard" confirmation first.
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

### Step 5: Cleanup Worktree

For Options 1, 2, 4:
```bash
git worktree remove <worktree-path>
```

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge | Yes | - | - | Yes |
| 2. PR | - | Yes | Yes | - |
| 3. Keep | - | - | Yes | - |
| 4. Discard | - | - | - | Force delete |

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request

## Integration

**Called by:**
- **subagent-driven-development** - After all tasks complete
- **executing-plans** - After all batches complete

**Pairs with:**
- **using-git-worktrees** - Cleans up worktree created there

**See also:**
- [Platform CLI Setup](references/platform-cli-setup.md) - Install and configure gh, glab, az
