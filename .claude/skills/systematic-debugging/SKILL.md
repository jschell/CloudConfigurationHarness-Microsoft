---
name: systematic-debugging
description: Use when debugging issues, before attempting any fix - requires finding root cause first through investigation, not symptom-fixing
---

# Systematic Debugging

## Overview

Find root cause before attempting fixes. Symptom fixes are failure.

**Core principle:** "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST."

## The Four Phases

### Phase 1: Root Cause Investigation

1. **Read error messages carefully** - they often tell you exactly what's wrong
2. **Reproduce consistently** - if you can't reproduce, you can't verify the fix
3. **Examine recent changes** - what changed since it last worked?
4. **Gather evidence** - logs, stack traces, data states
5. **Trace backward** - from symptom to origin

### Phase 2: Pattern Analysis

1. **Find working examples** - what's similar that does work?
2. **Study complete implementations** - don't guess at how things work
3. **Identify specific differences** - between broken and working
4. **Map dependencies** - what does this rely on?

### Phase 3: Hypothesis and Testing

1. **Form explicit hypothesis** - "I believe X causes Y because Z"
2. **Test with minimal change** - one variable at a time
3. **If wrong, form new hypothesis** - don't randomly try things
4. **Document what you learn** - even dead ends teach something

### Phase 4: Implementation

1. **Write failing test first** - captures the bug
2. **Apply single targeted fix** - address root cause only
3. **Verify test passes** - confirms fix works
4. **Check for regressions** - run full test suite

## The Three-Attempt Rule

```
IF three fix attempts each reveal different problems elsewhere:
  STOP - this signals architectural issues, not isolated bugs
  Discuss design with your human partner
  Don't keep patching
```

## Warning Signs You're Violating the Process

- Proposing solutions before tracing data flow
- Attempting multiple changes simultaneously
- "Just one more fix" after multiple failures
- Guessing instead of investigating
- Not reproducing before fixing

**When you see these:** Return to Phase 1.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Jump to fix immediately | Investigate root cause first |
| Multiple changes at once | One change, test, repeat |
| Ignore error messages | Read them carefully - they help |
| Can't reproduce but "fix" anyway | No repro = no verification |
| Patch symptoms | Find and fix root cause |

## Quick Debugging Questions

1. What exactly is the error/symptom?
2. When did it start happening?
3. What changed since it worked?
4. Can I reproduce it consistently?
5. What does the error message say?
6. What's the data state at failure point?
7. Is there a working example to compare?

## The Bottom Line

**Investigate → Understand → Hypothesize → Test → Fix**

Never: Fix → Hope → Repeat
