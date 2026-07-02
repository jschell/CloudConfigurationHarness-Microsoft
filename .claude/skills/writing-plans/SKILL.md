---
name: writing-plans
description: Use when you need to create a detailed implementation plan for a multi-step feature or task before coding begins
---

# Writing Plans

## Overview

Create comprehensive implementation plans for multi-step tasks.

**Core principle:** Plans are written for engineers with minimal codebase context. Clarity and actionability above all.

## Plan Characteristics

**Granularity:** Each step is one action (2-5 minutes)
- Write test
- Verify failure
- Implement
- Verify pass
- Commit

**Required elements:**
- Exact file paths and line numbers
- Complete code samples (not vague descriptions)
- Specific commands with expected outputs
- Clear task breakdown

**Philosophy:** DRY, YAGNI, TDD, frequent commits

## Plan Structure

Save to: `docs/plans/YYYY-MM-DD-<feature-name>.md`

```markdown
# Feature: [Name]

## Goal
[One sentence]

## Architecture
[Brief explanation of approach]

## Tech Stack
[Relevant technologies]

## Tasks

### Task 1: [Name]
**File:** `path/to/file.ts`

#### Steps:
1. Write test for [behavior]
   ```typescript
   // Complete test code
   ```
2. Run tests - expect failure
3. Implement [feature]
   ```typescript
   // Complete implementation code
   ```
4. Run tests - expect pass
5. Commit: "[message]"

### Task 2: [Name]
...
```

## Execution Models

### Subagent-Driven
- Fresh subagent per task
- Review checkpoints between tasks
- Stay in current session

### Parallel Session
- Separate session for execution
- Batch tasks together
- Async from planning

## Key Requirements

- Treat reader as competent but unfamiliar with codebase
- Include ALL necessary context
- No assumptions about what's "obvious"
- Complete, runnable code samples

## Integration

**Created by:**
- **brainstorming** - After design is validated

**Executed by:**
- **executing-plans** - Batch execution with checkpoints
- **subagent-driven-development** - Per-task execution
