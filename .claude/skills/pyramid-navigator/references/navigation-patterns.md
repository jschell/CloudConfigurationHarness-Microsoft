# Pyramid Navigation Patterns

Scenario-based workflows for `pyramid_cli.py`. All commands assume you're in the project root.

---

## Scenario: Find Where a Feature Lives

```bash
pyramid_cli.py query "authentication" --level 8
pyramid_cli.py query "authentication" --level 16 --type file
pyramid_cli.py get src/auth/handler.py --level 32
pyramid_cli.py get src/auth/handler.py --level 64   # if still unclear
```

---

## Scenario: Understand a Bug Report

```bash
# Start from the named symbol
pyramid_cli.py query "PaymentProcessor" --level 16 --type class
pyramid_cli.py get src/payments.py --level 32 --type function

# Find callers
pyramid_cli.py query "charge" --level 16 --type function

# Code only when summary is ambiguous
pyramid_cli.py get src/payments.py --level 64 --show-code
```

---

## Scenario: Map Dependencies Before Refactoring

```bash
pyramid_cli.py list --level 4                          # architecture overview
pyramid_cli.py query "MODULE_NAME" --level 16          # find all references
pyramid_cli.py get src/dependent.py --level 32         # check each dependent
```

---

## Scenario: Onboard to Unfamiliar Repo

```bash
pyramid_cli.py list --level 4                          # what does this project contain?
pyramid_cli.py query "main entry cli" --level 8        # entry points
pyramid_cli.py query "model schema dataclass" --level 16 --type class
pyramid_cli.py list --level 16                         # full file inventory
```

---

## Scenario: Find Test Coverage Gaps

```bash
pyramid_cli.py query "test" --level 8 --type file
pyramid_cli.py list --level 32 --type function         # tested functions
pyramid_cli.py get src/module.py --level 32 --type function  # source functions
```

---

## Scenario: Codebase Changed — Re-index

```bash
# Only re-processes files whose content hash changed
pyramid_cli.py analyze .

# Force full re-index (e.g. after prompt changes)
pyramid_cli.py analyze . --force
```

---

## Level Guide

| Level | Granularity | Best For |
|-------|-------------|---------|
| 4 | Module headline | Architecture overview |
| 8 | Subsystem description | Topic location |
| 16 | File with key exports | Identifying relevant files |
| 32 | Signatures + docstrings | Understanding contracts |
| 64 | Full logic summary | Pre-code-review inspection |
| `--show-code` | Raw source | Implementation ground truth |

---

## Type Filters

| Flag | Returns |
|------|---------|
| `--type file` | Source file nodes |
| `--type class` | Class/struct definitions |
| `--type function` | Function/method definitions |
| `--type all` | All node types |
| (none) | Defaults to `file` for `list`, all for `query` |

---

## Query Tips

- Combine semantic + structural: `query "retry logic" --level 16 --type function`
- Too many results: raise level (`--level 32` narrows to more specific matches)
- Too few results: lower level or broaden search terms
- Path search works too: `query "auth/"` matches on file paths

---

## Anti-Patterns

| Avoid | Do instead |
|-------|-----------|
| `get file.py --show-code` immediately | Start at level 4, refine down |
| `list --level 64` on large repos | Use `query` first to narrow |
| Reading every file at level 32 | Filter with level 16 query first |
| Skipping `init` if `.pyramid/` missing | Always run `pyramid-setup.py` first |
| Running `analyze` after every edit | Run once; re-run only after meaningful changes |

---

## Storage Layout

```
.pyramid/
├── config.json          # {"version": 1, "api": "anthropic", "created": "..."}
├── index.json           # {sha256: {path, element_type, name, levels: {4,8,16}}}
└── data/
    └── <sha256>.json    # {path, element_type, name, code, start_line, end_line, levels: {4..64}}
```

- `index.json` — loaded for every `query`/`list` call; kept small (levels 4/8/16 only)
- `data/<sha>.json` — read on `get`; levels 32/64 generated on first access and cached here
- SHA is `sha256(element.code)` — content-addressed, enables automatic change detection
