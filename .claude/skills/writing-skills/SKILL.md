---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

Writing skills IS Test-Driven Development applied to process documentation.

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## The Iron Law

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Same as TDD for code - write test (scenario), watch fail (baseline), write skill, watch pass.

## What is a Skill?

A skill is a reference guide for proven techniques, patterns, or tools.

**Skills are:** Reusable techniques, patterns, tools, reference guides
**Skills are NOT:** Narratives about how you solved a problem once

## When to Create

**Create when:**
- Technique wasn't intuitively obvious
- You'd reference this again across projects
- Pattern applies broadly

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Project-specific conventions (put in CLAUDE.md)

## SKILL.md Structure

```markdown
---
name: skill-name-with-hyphens
description: Use when [triggering conditions and symptoms]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases. When NOT to use.

## Core Pattern
Before/after code comparison (for techniques).

## Quick Reference
Table or bullets for scanning.

## Common Mistakes
What goes wrong + fixes.
```

## Frontmatter Rules

- **name:** Letters, numbers, hyphens only
- **description:** Start with "Use when...", < 500 chars
- **description:** ONLY triggering conditions, NOT workflow summary

## Token Efficiency

**Targets:**
- Frequently-loaded skills: < 200 words
- Other skills: < 500 words

**Techniques:**
- Reference --help instead of documenting flags
- Cross-reference other skills
- One excellent example, not many mediocre ones

## RED-GREEN-REFACTOR for Skills

### RED: Baseline Test
Run scenario WITHOUT skill. Document what agents naturally do wrong.

### GREEN: Write Minimal Skill
Address those specific failures. Run scenario WITH skill - verify compliance.

### REFACTOR: Close Loopholes
Agent found new rationalization? Add counter. Re-test.

## Quality Checklist

- [ ] Name uses only letters, numbers, hyphens
- [ ] Description starts with "Use when..."
- [ ] Description has NO workflow summary
- [ ] Tested baseline behavior first
- [ ] Tested with skill present
- [ ] < 500 words (< 200 for core skills)

## The Bottom Line

Creating skills IS TDD for documentation.

Same cycle: RED → GREEN → REFACTOR
Same benefits: Better quality, fewer surprises.
