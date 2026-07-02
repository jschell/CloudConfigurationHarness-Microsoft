---
name: brainstorming
description: Use when starting new features or projects that need design exploration - helps turn ideas into fully-formed designs through collaborative dialogue before implementation
---

# Brainstorming

## Overview

Turn ideas into fully-formed designs through collaborative dialogue.

**Core principle:** Understand deeply, explore alternatives, validate in chunks.

## The Process

### Phase 1: Understand the Idea

Ask targeted questions to understand:
- What problem are we solving?
- Who is this for?
- What does success look like?
- What constraints exist?

**One question at a time** - don't overwhelm.
**Prefer multiple-choice** when feasible.

### Phase 2: Explore Approaches

Before settling on a solution:
- Identify 2-3 alternative approaches
- Consider trade-offs for each
- Discuss with your human partner

**Follow YAGNI** - ruthlessly remove unnecessary features.

### Phase 3: Present Design

Break design into 200-300 word sections:
1. Present one section
2. Get validation
3. Move to next section

**Coverage areas:**
- Architecture overview
- Key components
- Data flow
- Error handling
- Testing approach

### Phase 4: Document and Proceed

After validation:
1. Write design to markdown file
2. Commit to git
3. Proceed to implementation planning

**Use isolated workspace** - set up git worktree before implementation.

## Key Principles

- Ask, don't assume
- Explore alternatives before committing
- Validate in small chunks
- YAGNI - remove what's not needed
- Document before implementing

## When to Revisit

Return to brainstorming when:
- Requirements change significantly
- Approach hits fundamental blockers
- Your human partner questions the direction

## Integration

**Leads to:**
- **writing-plans** - Create implementation plan from design
- **using-git-worktrees** - Set up isolated workspace
