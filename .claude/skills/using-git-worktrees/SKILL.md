---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection
---

# Using Git Worktrees

## Overview

Git worktrees create isolated workspaces sharing the same repository.

**Core principle:** Systematic directory selection + safety verification = reliable isolation.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Directory Selection

### Priority Order

1. **Check existing directories:**
   ```bash
   ls -d .worktrees 2>/dev/null     # Preferred (hidden)
   ls -d worktrees 2>/dev/null      # Alternative
   ```

2. **Check CLAUDE.md** for preference

3. **Ask user** if neither exists

### Safety Verification

**For project-local directories:**

```bash
# Verify directory is ignored
git check-ignore -q .worktrees 2>/dev/null
```

**If NOT ignored:**
1. Add to .gitignore
2. Commit the change
3. Then proceed

## Creation Steps

```bash
# 1. Get project name
project=$(basename "$(git rev-parse --show-toplevel)")

# 2. Create worktree
git worktree add .worktrees/$BRANCH_NAME -b $BRANCH_NAME
cd .worktrees/$BRANCH_NAME

# 3. Run project setup
if [ -f package.json ]; then npm install; fi
if [ -f Cargo.toml ]; then cargo build; fi
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# 4. Verify clean baseline
npm test  # or appropriate test command
```

### Report Ready

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| `.worktrees/` exists | Use it (verify ignored) |
| `worktrees/` exists | Use it (verify ignored) |
| Both exist | Use `.worktrees/` |
| Neither exists | Check CLAUDE.md → Ask user |
| Directory not ignored | Add to .gitignore + commit |
| Tests fail | Report failures + ask |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skip ignore verification | Always check before creating |
| Assume directory location | Follow priority order |
| Proceed with failing tests | Report and ask |
| Hardcode setup commands | Auto-detect from project files |

## Integration

**Called by:**
- **brainstorming** - When design approved
- **subagent-driven-development** - Before executing tasks
- **executing-plans** - Before executing tasks

**Pairs with:**
- **finishing-a-development-branch** - Cleanup after work complete
