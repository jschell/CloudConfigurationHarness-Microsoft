---
name: requesting-code-review
description: Use when you need code reviewed - dispatches code-reviewer subagent with proper context
---

# Requesting Code Review

## Overview

Request code reviews at key checkpoints using a structured approach.

**Core principle:** Review early, review often.

## When to Request

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

## The Process

### Step 1: Get Commit Range

```bash
git log --oneline -n 5  # Recent commits
git rev-parse HEAD      # Current commit
```

### Step 2: Dispatch Reviewer

Provide:
- What was built
- Relevant requirements/specs
- Commit range affected

### Step 3: Handle Response

**Critical issues:** Fix immediately
**Important issues:** Fix before proceeding
**Minor concerns:** Can address later

## Response Handling

- Take feedback seriously
- Push back if reviewer is wrong (with reasoning)
- Use **receiving-code-review** skill for implementation

## Workflow Integration

| Development Style | When to Review |
|------------------|----------------|
| Subagent-driven | Per-task reviews |
| Plan execution | Every 3 tasks (batch) |
| Ad-hoc | Pre-merge |

## The Bottom Line

Code review is a quality gate, not a final checkpoint.

Request reviews throughout development, not just at the end.
