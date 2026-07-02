---
name: project-setup
description: Use when setting up a new project for Claude Code, creating or updating CLAUDE.md, or configuring project context - helps establish project conventions and commands
---

# Project Setup

## Overview

Configure a project for effective Claude Code usage by creating CLAUDE.md.

**Core principle:** CLAUDE.md provides project context that persists across sessions.

## Context Files

| File | Purpose | Location |
|------|---------|----------|
| `AGENTS.md` | Universal context for Cursor, Windsurf, Copilot | Project root |
| `.claude/CLAUDE.md` | Claude Code instructions (auto-discovered) | `.claude/` directory |

**Contents:** Project stack, commands (test/lint/build), rules, stop conditions.

## When to Create

- New project setup
- Onboarding to existing project
- Adding Claude Code to a project
- Project conventions have changed

## Setup Process

### Step 1: Analyze Project

```
1. Check for existing CLAUDE.md
2. Identify package manager (package.json, pyproject.toml, etc.)
3. Find test/lint/build commands
4. Note project structure
```

### Step 2: Create Context Files

**Recommended structure:**
```
project/
├── AGENTS.md          # For Cursor/Windsurf/Copilot
└── .claude/
    └── CLAUDE.md      # Detailed instructions (Claude Code reads automatically)
```

**AGENTS.md (root):**
```markdown
# Agent Instructions
@.claude/CLAUDE.md
```

**.claude/CLAUDE.md:**
```markdown
# Project: [Name]

## Commands
- Test: `npm test`
- Lint: `npm run lint`
- Build: `npm run build`

## Rules
[Project-specific constraints]
```

No root `CLAUDE.md` needed - Claude Code auto-discovers `.claude/CLAUDE.md`.

**Full template:** See [references/claude-md-template.md](references/claude-md-template.md)

### Step 3: Verify

```
1. Run each command to verify it works
2. Check CLAUDE.md is readable
3. Test that context loads in new session
```

## Context File Sections

| Section | Purpose | Required |
|---------|---------|----------|
| Project name | Identification | Yes |
| Commands | Test, lint, build | Yes |
| Stack | Language, framework | Recommended |
| Rules | Project constraints | Recommended |
| Stop conditions | When to ask human | Optional |

## Multi-Tool Compatibility

- Claude Code: Auto-reads `.claude/CLAUDE.md`
- Other tools: Use `AGENTS.md` with `@.claude/CLAUDE.md` reference
- Single source of truth, no duplicate file names

See [references/multi-tool-setup.md](references/multi-tool-setup.md) for details.

## Common Patterns

**Monorepo:**
```markdown
## Workspaces
- packages/core - Core library
- packages/cli - CLI tool
- apps/web - Web app

## Commands
Run from workspace: `npm test -w packages/core`
```

**Python project:**
```markdown
## Commands
- Test: `uv run --frozen pytest`
- Lint: `uv run --frozen ruff check . --fix`
- Type check: `uv run --frozen pyright`
- Format: `uv run --frozen ruff format .`
```
Full conventions (package management, testing, exceptions): see [python-standards](../python-standards/SKILL.md).

**With autonomous work:**
```markdown
## Autonomous Work
Plans: docs/plans/{1_backlog,2_active,3_complete}/
Stop if: 3 failures, breaking changes, security issues
```

## Integration

**Used by:**
- **autonomous-work** - Reads project context and commands
- Any Claude Code session - Project context loads automatically

**See also:**
- [Full CLAUDE.md Template](references/claude-md-template.md)
- [Multi-Tool Setup](references/multi-tool-setup.md)
