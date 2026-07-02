---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

# Dispatching Parallel Agents

## Overview

When multiple unrelated problems exist, investigating them sequentially wastes time.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Problems can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related
- Full system state needed to understand
- Agents would interfere with each other
- Still exploring what's broken

## The Pattern

### Step 1: Identify Independent Domains

Group failures by what's broken:
- Domain A: Tool approval failures
- Domain B: Batch completion failures
- Domain C: Abort functionality failures

Each domain stands alone.

### Step 2: Create Focused Agent Tasks

Each agent receives:
- Specific scope (one domain only)
- Clear goal
- Constraints
- Expected output

**Example prompt:**
```
Fix tool approval failures in agent-tool-approve.test.ts

Scope: Only this file
Goal: All tests passing
Constraints: Don't modify other test files
Output: Summary of changes made
```

### Step 3: Dispatch in Parallel

Use Task tool to create multiple agents simultaneously.

### Step 4: Review and Integrate

1. Read summaries from each agent
2. Verify fixes don't conflict
3. Run full test suite
4. Integrate changes

## Agent Prompt Structure

```
[Problem domain and scope]

Scope: [specific files/area]
Goal: [clear success criteria]
Constraints: [what NOT to do]
Output: [what to report back]
```

**Good:** "Fix agent-tool-abort.test.ts"
**Bad:** "Fix all the tests"

## Benefits

- **Parallelization** - Multiple investigations at once
- **Narrow scope** - Less context per agent
- **Independence** - No interference between agents
- **Speed** - Concurrent work
