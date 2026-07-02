---
name: feature-backlog
description: Use when managing feature lists for autonomous work sessions - simple format for tracking features through planning and execution
---

# Feature Backlog

## Overview

Simple format for tracking features through autonomous work phases.

**Core principle:** One feature in progress at a time.

## Format

```markdown
# Feature Backlog

## In Progress
- [ ] Current feature → docs/plans/2_active/feature-name.md

## Todo
- [ ] Next feature
- [ ] Another feature

## Done
- [x] Completed feature (2025-01-29)
```

## Rules

| Rule | Why |
|------|-----|
| One in-progress at a time | Prevents scope creep, context loss |
| Link to plan in 2_active/ | Connects backlog to execution |
| Mark done only after tests pass | Ensures quality gate |
| Add completion date | Tracks velocity |

## State Transitions

```
Todo → In Progress (when plan moves to 2_active/)
       Link to docs/plans/2_active/feature.md

In Progress → Done (when plan moves to 3_complete/)
              Add completion date
```

## Alternatives

If using issue trackers instead (GitHub, GitLab, Jira, etc.):
- Label `in-progress` for current feature
- Reference plan in issue comments
- Close issue when complete

## Integration

**Used by:**
- **autonomous-work** - Identifies next feature to work on
