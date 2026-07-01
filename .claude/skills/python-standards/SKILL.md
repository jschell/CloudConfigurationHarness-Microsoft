---
name: python-standards
description: Use when starting, reviewing, or configuring a Python project - establishes uv-only package management, ruff/pyright tooling, pytest conventions, and type/docstring/exception-handling defaults
---

# Python Standards

## Overview

Default engineering conventions for Python projects. Apply unless the project's existing CLAUDE.md or config overrides them.

**Core principle:** uv for everything, strict typing, tests mirror source.

## Package Management

- Use `uv` exclusively — never `pip install` or `uv pip install`
- Install: `uv add <package>`
- Upgrade: `uv add --dev <package> --upgrade-package <package>`
- Run tools without touching the lockfile: `uv run --frozen <tool>`
- Cross-version test: `uv run --frozen --python 3.10 pytest`
- No `@latest` pins — pin explicit versions
- Editing dependencies: change `pyproject.toml` by hand, then `uv lock`

## Code Quality

- Type hints on all function signatures
- Docstrings on public APIs; include a `Raises:` section for exceptions callers should catch
- Explicit `__all__` in `__init__.py` to define the public surface
- Imports at the top of the file only — exception: lazy imports for optional dependencies
- Keep functions focused and concise, following existing patterns
- Line length: Ruff defaults to 88 — check `pyproject.toml` for a project override before assuming a limit

## Formatting, Linting, Type Checking

| Task | Command |
|------|---------|
| Format | `uv run --frozen ruff format .` |
| Lint + fix | `uv run --frozen ruff check . --fix` |
| Type check | `uv run --frozen pyright` |

Wire these into a pre-commit hook so format/lint run automatically on every commit.

## Testing

- `uv run --frozen pytest`, plain `test_*` functions — no `Test`-prefixed classes
- Test tree mirrors source tree: `src/pkg/client/foo.py` → `tests/client/test_foo.py`
- Async tests: use `anyio`, not `asyncio` — wait on `anyio.Event` / `stream.receive()`, never fixed `sleep()`
- Wrap indefinite waits in `anyio.fail_after(5)` to prevent hangs
- New features and bug fixes both need test coverage, including edge cases and error paths
- Target full branch coverage

## Exception Handling

- Catch specific exceptions — broad `except Exception:` only in top-level handlers
- Use `logger.exception()` (not `logger.error()`) when swallowing an exception without including its details in the message

## Git Conventions

- Bug fix / user-reported issue: add trailer `git commit --trailer "Reported-by:<name>"`
- GitHub issue: add trailer `git commit --trailer "Github-Issue:#<number>"`
- PR descriptions: lead with the problem and solution approach, not a line-by-line diff walkthrough

These commit-trailer conventions are project-level defaults — they don't override any explicit harness or session instruction about commit attribution (e.g. required co-author trailers), which always takes precedence.

## Integration

**Used by:**
- **repo-init** — apply when scaffolding a Python stack
- **project-setup** — source for the Python `## Commands` block in CLAUDE.md

## Sources

- [modelcontextprotocol/python-sdk AGENTS.md](https://github.com/modelcontextprotocol/python-sdk/blob/main/AGENTS.md)
- [jschell/AgentConfig PythonSDK_CLAUDE.md](https://github.com/jschell/AgentConfig/blob/main/_sources/PythonSDK_CLAUDE.md)

Generalized beyond MCP-specific projects.
