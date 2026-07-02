---
name: pyramid-navigator
description: Use when navigating an unfamiliar codebase indexed with pyramid-cli — search multi-level summaries progressively before reading source code
allowed-tools: Bash
---

# Pyramid Navigator

Navigate codebases indexed with pyramid-cli using progressive refinement: broad first, code only when necessary.

## Setup

```bash
uv run scripts/pyramid-setup.py [--analyze [PATH]]
```

Or manually:
```bash
uv run scripts/pyramid_cli.py init
uv run scripts/pyramid_cli.py analyze .
```

> **`.pyramid/` location:** Always `init` and `analyze` from the **root of the repo being analyzed** — the `.pyramid/` directory is created in the current working directory. If analyzing a repo at `/path/to/project`, run commands with that as CWD or pass it explicitly: `analyze /path/to/project`. Do not create `.pyramid/` inside the pyramid-navigator skill directory itself.

No API key needed when running inside Claude Code — uses `claude` CLI automatically.

## Core Commands

| Command | Purpose |
|---------|---------|
| `uv run scripts/pyramid_cli.py list [--level N] [--type file\|function\|class]` | Browse all elements |
| `uv run scripts/pyramid_cli.py query QUERY [--level N] [--type ...]` | Search by concept |
| `uv run scripts/pyramid_cli.py get ELEMENT_PATH [--level N] [--show-code]` | Inspect element |
| `uv run scripts/pyramid_cli.py analyze [PATH] [--force] [--no-llm]` | (Re)index codebase |

**Levels:** 4=compressed, 8=scannable, 16=summary, 32=detailed, 64=comprehensive

## Progressive Refinement Protocol

Follow this order — stop as soon as you have enough context.

### Step 1: Orient (level 4-8)
```bash
uv run scripts/pyramid_cli.py list --level 4
uv run scripts/pyramid_cli.py query "TOPIC" --level 8
```

### Step 2: Locate (level 16)
```bash
uv run scripts/pyramid_cli.py query "TOPIC" --level 16 --type file
```

### Step 3: Understand (level 32)
```bash
uv run scripts/pyramid_cli.py get src/module.py --level 32
```

### Step 4: Deep dive (level 64)
```bash
uv run scripts/pyramid_cli.py get src/module.py --level 64
```

### Step 5: Code (last resort)
```bash
uv run scripts/pyramid_cli.py get src/module.py --level 64 --show-code
```

## Decision Rules

- Answer found at level N → stop, do not go deeper
- Specific concept → use `query` before `list`
- Multiple candidates at level 16 → `get` each at level 32 to compare
- Unfamiliar project → always start with `list --level 4`
- Re-index after code changes → `analyze .` (skips unchanged files via content hash)
- Always `init`/`analyze` from the target repo root — `.pyramid/` is created in CWD
- `.gs` files (Google Apps Script) are indexed as JavaScript — functions and classes extracted normally
- `.ps1`/`.psm1` files (PowerShell) are indexed via tree-sitter (requires `tree-sitter-language-pack`) or regex fallback

## See Also

- [Navigation Patterns](references/navigation-patterns.md) — scenario-based workflows
- [pyramid_cli.py](scripts/pyramid_cli.py) — the CLI tool (PEP 723 inline deps, `uv run`)
- [pyramid-setup.py](scripts/pyramid-setup.py) — dependency installer
