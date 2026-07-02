#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "click>=8.0",
#   "anthropic>=0.40",
# ]
# [tool.uv]
# exclude-newer = "2026-02-12T00:00:00Z"
# ///
# Optional extras (install separately if needed):
#   uv add tree-sitter-language-pack   # multi-language parsing, 165+ langs incl. PowerShell (recommended)
#   uv add openai                      # OpenAI provider alternative
"""pyramid_cli.py — Pyramid Summary Generator CLI.

Indexes a codebase with multi-level LLM summaries for progressive navigation.

Usage:
    uv run pyramid_cli.py init
    uv run pyramid_cli.py analyze [PATH]
    uv run pyramid_cli.py query QUERY [--level N]
    uv run pyramid_cli.py get ELEMENT_PATH [--level N] [--show-code]
    uv run pyramid_cli.py list [--level N] [--type file|function|class]

Storage layout (.pyramid/):
    config.json         Project configuration
    index.json          Fast search index (levels 4, 8, 16 only)
    data/<sha256>.json  Full element data (all levels + source code)

Environment variables:
    ANTHROPIC_API_KEY   Anthropic provider (default)
    OPENAI_API_KEY      OpenAI provider (use --api openai)
    PYRAMID_DB          Override .pyramid/ directory location
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import click

logger = logging.getLogger(__name__)

# ── Optional dependencies (fail gracefully if absent) ──────────────────────

try:
    import anthropic as _anthropic

    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

try:
    import openai as _openai

    _OPENAI_AVAILABLE = True
except ImportError:
    _openai = None  # type: ignore[assignment]
    _OPENAI_AVAILABLE = False

try:
    import tree_sitter_language_pack as _ts_languages

    _TREE_SITTER_AVAILABLE = True
except ImportError:
    _ts_languages = None  # type: ignore[assignment]
    _TREE_SITTER_AVAILABLE = False


# ─────────────────────────────────────────────
# SECTION: Data structures
# ─────────────────────────────────────────────


@dataclass
class Element:
    """A parsed code element: a file, class, or function."""

    path: str
    element_type: str  # "file" | "class" | "function"
    name: str
    code: str
    start_line: int
    end_line: int

    def content_hash(self) -> str:
        """SHA-256 of the element's source code."""
        return hashlib.sha256(self.code.encode()).hexdigest()


# ─────────────────────────────────────────────
# SECTION: Storage
# ─────────────────────────────────────────────

_INDEX_LEVELS = (4, 8, 16)  # Levels stored in index.json (hot path)


class StorageManager:
    """Read and write the .pyramid/ directory."""

    VERSION = 1

    def __init__(self, pyramid_dir: Path) -> None:
        self.pyramid_dir = pyramid_dir
        self.data_dir = pyramid_dir / "data"
        self.index_path = pyramid_dir / "index.json"
        self.config_path = pyramid_dir / "config.json"

    def init(self, api: str = "anthropic") -> None:
        """Create .pyramid/ directory structure."""
        self.pyramid_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        if not self.config_path.exists():
            _write_json(self.config_path, {
                "version": self.VERSION,
                "created": datetime.now(timezone.utc).isoformat(),
                "api": api,
            })

        if not self.index_path.exists():
            _write_json(self.index_path, {})

    def is_initialized(self) -> bool:
        """Return True if .pyramid/ has been initialized."""
        return self.pyramid_dir.exists() and self.index_path.exists()

    def load_config(self) -> dict[str, object]:
        """Load config.json, returning empty dict if missing."""
        if not self.config_path.exists():
            return {}
        return _read_json(self.config_path)

    def load_index(self) -> dict[str, dict[str, object]]:
        """Load index.json, returning empty dict if missing."""
        if not self.index_path.exists():
            return {}
        return _read_json(self.index_path)

    def save_index(self, index: dict[str, dict[str, object]]) -> None:
        """Persist index.json."""
        _write_json(self.index_path, index)

    def load_data(self, sha: str) -> dict[str, object] | None:
        """Load data/<sha>.json, returning None if missing."""
        path = self.data_dir / f"{sha}.json"
        if not path.exists():
            return None
        return _read_json(path)

    def save_data(self, sha: str, data: dict[str, object]) -> None:
        """Persist data/<sha>.json."""
        _write_json(self.data_dir / f"{sha}.json", data)


def _read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _write_json(path: Path, data: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# SECTION: Parser
# ─────────────────────────────────────────────

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".gs": "javascript",  # Google Apps Script — parsed as JavaScript
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".ps1": "powershell",
    ".psm1": "powershell",  # PowerShell module files — same syntax as .ps1
}

_IGNORE_DIRS = frozenset({
    ".git", ".pyramid", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".env", "dist", "build", "target", ".tox", ".pytest_cache",
    ".mypy_cache", "coverage", ".coverage", "htmlcov",
})

_IGNORE_SUFFIXES = frozenset({".min.js", ".min.css", ".lock"})
_IGNORE_NAMES = frozenset({"package-lock.json", "yarn.lock", "Pipfile.lock", "poetry.lock"})

# tree-sitter node types per language
_FUNC_TYPES: dict[str, list[str]] = {
    "python": ["function_definition", "async_function_definition"],
    "javascript": ["function_declaration", "arrow_function", "method_definition"],
    "typescript": ["function_declaration", "arrow_function", "method_definition"],
    "go": ["function_declaration", "method_declaration"],
    "rust": ["function_item"],
    "java": ["method_declaration", "constructor_declaration"],
    "c": ["function_definition"],
    "cpp": ["function_definition"],
    "ruby": ["method"],
    "php": ["function_definition", "method_declaration"],
    "powershell": ["function_statement", "filter_statement"],
}
_CLASS_TYPES: dict[str, list[str]] = {
    "python": ["class_definition"],
    "javascript": ["class_declaration"],
    "typescript": ["class_declaration"],
    "java": ["class_declaration"],
    "ruby": ["class"],
    "php": ["class_declaration"],
    "rust": ["impl_item", "struct_item"],
    "go": ["type_declaration"],
    "c": ["struct_specifier"],
    "cpp": ["class_specifier", "struct_specifier"],
    "powershell": ["class_statement"],
}


def _should_ignore(path: Path) -> bool:
    return (
        path.name in _IGNORE_NAMES
        or path.suffix.lower() in _IGNORE_SUFFIXES
        or any(part in _IGNORE_DIRS for part in path.parts)
    )


class CodeParser:
    """Extract code elements (file/class/function) from source files."""

    def parse_file(self, path: Path, root: Path) -> list[Element]:
        """Return all elements found in *path*. Always includes a file-level element."""
        relative = str(path.relative_to(root))
        try:
            code = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            logger.exception("Failed to read %s", path)
            return []

        file_element = Element(
            path=relative,
            element_type="file",
            name=path.name,
            code=code,
            start_line=1,
            end_line=len(code.splitlines()),
        )

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return [file_element]

        lang = SUPPORTED_EXTENSIONS[suffix]
        sub_elements = (
            self._parse_tree_sitter(code, relative, lang)
            if _TREE_SITTER_AVAILABLE
            else self._parse_heuristic(code, relative, suffix)
        )
        return [file_element, *sub_elements]

    @staticmethod
    def _parse_tree_sitter(code: str, relative: str, lang: str) -> list[Element]:
        """Use tree-sitter to extract function and class elements."""
        if _ts_languages is None:
            return []

        try:
            parser = _ts_languages.get_parser(lang)
        except Exception:
            logger.exception("tree-sitter parser unavailable for %s", lang)
            return []

        tree = parser.parse(code.encode())
        lines = code.splitlines()
        elements: list[Element] = []
        lang_func_types = set(_FUNC_TYPES.get(lang, []))
        lang_class_types = set(_CLASS_TYPES.get(lang, []))

        def _extract_name(node: object) -> str:
            for child in node.children:  # type: ignore[attr-defined]
                if child.type in (  # type: ignore[attr-defined]
                    "identifier", "name", "field_identifier", "property_identifier"
                ):
                    text = child.text  # type: ignore[attr-defined]
                    return text.decode() if text else ""
            return node.type  # type: ignore[attr-defined]

        def _walk(node: object) -> None:
            node_type = node.type  # type: ignore[attr-defined]
            if node_type in lang_func_types or node_type in lang_class_types:
                etype = "function" if node_type in lang_func_types else "class"
                name = _extract_name(node)
                start = node.start_point[0]  # type: ignore[attr-defined]
                end = node.end_point[0]  # type: ignore[attr-defined]
                elements.append(Element(
                    path=relative,
                    element_type=etype,
                    name=name,
                    code="\n".join(lines[start : end + 1]),
                    start_line=start + 1,
                    end_line=end + 1,
                ))
            for child in node.children:  # type: ignore[attr-defined]
                _walk(child)

        _walk(tree.root_node)
        return elements

    @staticmethod
    def _parse_heuristic(code: str, relative: str, suffix: str) -> list[Element]:
        """Line-based fallback parser for when tree-sitter is unavailable."""
        patterns: dict[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
            ".py": (
                re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\("),
                re.compile(r"^class\s+(\w+)"),
            ),
            ".go": (
                re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\("),
                re.compile(r"^type\s+(\w+)\s+struct"),
            ),
            ".rs": (
                re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]"),
                re.compile(r"^(?:pub\s+)?(?:struct|impl|enum)\s+(\w+)"),
            ),
            ".ps1": (
                re.compile(r"^(?:function|filter)\s+([\w][\w-]*)\s*(?:\(|{|\s*$)", re.IGNORECASE),
                re.compile(r"^class\s+(\w+)", re.IGNORECASE),
            ),
            ".psm1": (
                re.compile(r"^(?:function|filter)\s+([\w][\w-]*)\s*(?:\(|{|\s*$)", re.IGNORECASE),
                re.compile(r"^class\s+(\w+)", re.IGNORECASE),
            ),
        }
        default_func = re.compile(r"^(?:def|func|function|fn|sub)\s+(\w+)")
        default_class = re.compile(r"^(?:class|struct|interface|type)\s+(\w+)")
        func_pat, class_pat = patterns.get(suffix, (default_func, default_class))

        lines = code.splitlines()
        elements: list[Element] = []

        def _block_end(start: int) -> int:
            base_indent = len(lines[start]) - len(lines[start].lstrip())
            braces = lines[start].count("{") - lines[start].count("}")
            for i in range(start + 1, min(start + 200, len(lines))):
                stripped = lines[i].strip()
                if not stripped:
                    continue
                if "{" in lines[i] or "}" in lines[i]:
                    braces += lines[i].count("{") - lines[i].count("}")
                    if braces <= 0:
                        return i
                else:
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    if indent <= base_indent:
                        return i - 1
            return min(start + 50, len(lines) - 1)

        for i, line in enumerate(lines):
            m = func_pat.match(line) or class_pat.match(line)
            if not m:
                continue
            etype = "function" if func_pat.match(line) else "class"
            name = m.group(1)
            end = _block_end(i)
            elements.append(Element(
                path=relative,
                element_type=etype,
                name=name,
                code="\n".join(lines[i : end + 1]),
                start_line=i + 1,
                end_line=end + 1,
            ))

        return elements

    def walk_directory(self, root: Path, ignore_file: Path | None = None) -> list[Path]:
        """Return sorted list of parseable source files under *root*."""
        extra_patterns: list[str] = []
        for candidate in (ignore_file, root / ".gitignore"):
            if candidate and candidate.exists():
                for line in candidate.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        extra_patterns.append(line.lstrip("/"))

        results: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if _should_ignore(path):
                continue
            rel = str(path.relative_to(root))
            if any(pat in rel or rel.endswith(pat) for pat in extra_patterns):
                continue
            if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                results.append(path)

        return sorted(results)


# ─────────────────────────────────────────────
# SECTION: Summarizer
# ─────────────────────────────────────────────

_SUMMARY_PROMPT = """\
Summarize this code element at increasing word-count levels using iterative expansion.
Build each level by starting with the COMPLETE text of the previous shorter level, then append additional words.
Never alter the text already written for a shorter level — only append.

Return ONLY a JSON object: keys are word-count strings, values are the summaries.
Word counts must be exact.

Element type: {element_type}
Element name: {name}
File: {path}

Code:
```
{code}
```

Required word counts in ascending order: {levels}

Example for levels [4, 8, 16]:
{{
  "4":  "loads json config",
  "8":  "loads json config file from pyramid directory",
  "16": "loads json config file from pyramid directory structure returning empty dict when path missing"
}}

The "8" value starts with the exact "4" text. The "16" value starts with the exact "8" text.
Each entry is a strict prefix of all longer entries.
"""

_EXTEND_PROMPT = """\
Extend the following {seed_level}-word summary to exactly {target} words by appending new words after it.
Do NOT change the existing text — only add words after the last word.

Existing {seed_level}-word summary:
  {seed}

Return ONLY a JSON object: {{"{target}": "<the {target}-word summary that starts with the existing text>"}}
"""

_ANALYZE_LEVELS = (4, 8, 16)
LEVEL_SEQUENCE = (4, 8, 16, 32, 64)


class Summarizer:
    """Generate LLM summaries at multiple word-count levels."""

    def __init__(
        self,
        api: str = "anthropic",
        model: str | None = None,
        no_llm: bool = False,
    ) -> None:
        self.api = api
        self.model = model or self._default_model(api)
        self.no_llm = no_llm

    @staticmethod
    def _default_model(api: str) -> str:
        return "gpt-4o-mini" if api == "openai" else "claude-haiku-4-5-20251001"

    def _detect_provider(self) -> str:
        """Return the best available provider: anthropic | openai | claude-cli | stub."""
        if self.no_llm:
            return "stub"
        if self.api == "anthropic" and os.environ.get("ANTHROPIC_API_KEY") and _ANTHROPIC_AVAILABLE:
            return "anthropic"
        if self.api == "openai" and os.environ.get("OPENAI_API_KEY") and _OPENAI_AVAILABLE:
            return "openai"
        # Cross-fallback: any key available
        if os.environ.get("ANTHROPIC_API_KEY") and _ANTHROPIC_AVAILABLE:
            return "anthropic"
        if os.environ.get("OPENAI_API_KEY") and _OPENAI_AVAILABLE:
            return "openai"
        # Last resort: use the claude CLI if in PATH (works inside Claude Code sessions)
        if shutil.which("claude"):
            return "claude-cli"
        return "stub"

    def _call_provider(self, provider: str, prompt: str) -> str:
        """Dispatch a prompt to the named provider and return raw text."""
        if provider == "anthropic":
            return self._call_anthropic(prompt)
        if provider == "openai":
            return self._call_openai(prompt)
        return self._call_claude_cli(prompt)

    def summarize(
        self,
        element: Element,
        levels: tuple[int, ...] | list[int],
        seed: str | None = None,
        seed_level: int | None = None,
    ) -> dict[str, str]:
        """Return {str(level): summary} for each level.

        When *seed* is provided (a shorter summary that already exists) and only
        one level is requested, uses _EXTEND_PROMPT to append words rather than
        regenerate from scratch.  This preserves the prefix invariant.
        """
        provider = self._detect_provider()

        if provider == "stub":
            return {str(lvl): f"{element.element_type} {element.name}" for lvl in levels}

        sorted_levels = sorted(levels)

        if seed and len(sorted_levels) == 1:
            prompt = _EXTEND_PROMPT.format(
                seed_level=seed_level,
                target=sorted_levels[0],
                seed=seed,
            )
        else:
            code = element.code[:8000] + ("\n... (truncated)" if len(element.code) > 8000 else "")
            prompt = _SUMMARY_PROMPT.format(
                element_type=element.element_type,
                name=element.name,
                path=element.path,
                code=code,
                levels=sorted_levels,
            )

        try:
            raw = self._call_provider(provider, prompt)
            return self._parse_summaries(raw, levels)
        except (json.JSONDecodeError, KeyError, ValueError, RuntimeError, OSError):
            logger.exception("Failed to get summaries for %s", element.path)
            return {str(lvl): f"{element.element_type} {element.name}" for lvl in levels}

    def _call_anthropic(self, prompt: str) -> str:
        if _anthropic is None:
            raise RuntimeError("anthropic package not installed: uv add anthropic")
        client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=self.model,
            max_tokens=512,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def _call_openai(self, prompt: str) -> str:
        if _openai is None:
            raise RuntimeError("openai package not installed: uv add openai")
        client = _openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _call_claude_cli(prompt: str) -> str:
        """Invoke the claude CLI subprocess (works inside Claude Code sessions)."""
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr.strip()}")
        return result.stdout.strip()

    @staticmethod
    def _parse_summaries(
        raw: str, levels: tuple[int, ...] | list[int]
    ) -> dict[str, str]:
        """Extract JSON {level: summary} from an LLM response string."""
        try:
            data = json.loads(raw)
            return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            pass
        # Try to extract a JSON object from surrounding text
        m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                return {str(k): str(v) for k, v in data.items()}
            except json.JSONDecodeError:
                logger.exception("Failed to parse JSON from LLM response")
        return {str(lvl): raw.strip() for lvl in levels}


# ─────────────────────────────────────────────
# SECTION: CLI helpers
# ─────────────────────────────────────────────


def _pyramid_dir(db_path: str | None) -> Path:
    if db_path:
        return Path(db_path)
    env = os.environ.get("PYRAMID_DB")
    if env:
        return Path(env)
    return Path.cwd() / ".pyramid"


def _require_init(storage: StorageManager) -> None:
    if not storage.is_initialized():
        raise click.ClickException(
            ".pyramid/ not found. Run: uv run pyramid_cli.py init"
        )


# Ordered choices shown to the user when no guidance is found.
_AGENT_DOC_OPTIONS: list[tuple[str, str]] = [
    ("1", "CLAUDE.md"),
    ("2", "AGENTS.md"),
    ("3", ".claude/CLAUDE.md"),
]
# All candidate paths (same set, used for the existence check).
_AGENT_DOC_CANDIDATES = tuple(rel for _, rel in _AGENT_DOC_OPTIONS)

# Template written into the chosen file.  {script} and {skill} are filled with
# paths relative to the project root at runtime.
_AGENT_GUIDANCE_TEMPLATE = """
## Codebase Navigation

This project is indexed with pyramid-navigator for progressive code exploration.

### CLI quick-reference

```bash
uv run {script} list --level 4               # browse all elements at a glance
uv run {script} query "TOPIC" --level 8      # search by concept
uv run {script} get path/to/file.py --level 16  # inspect a specific element
```

Follow the Progressive Refinement Protocol — start at level 4–8, go deeper only when
necessary.  Full skill documentation and decision rules: {skill}
"""


def _check_agent_guidance(root: Path) -> bool:
    """Return True if any agent-convention file in *root* mentions pyramid.

    A loose keyword match is intentional — the goal is to detect that the
    author has thought about it, not to validate the content.
    """
    for candidate in _AGENT_DOC_CANDIDATES:
        path = root / candidate
        if path.exists():
            try:
                if "pyramid" in path.read_text(encoding="utf-8", errors="ignore").lower():
                    return True
            except OSError:
                pass
    return False


def _agent_guidance_snippet(root: Path) -> str:
    """Return the guidance markdown with paths relative to *root*."""
    here = Path(__file__).resolve()
    skill_md = here.parent.parent / "SKILL.md"  # skills/pyramid-navigator/SKILL.md
    try:
        script_rel = here.relative_to(root.resolve())
    except ValueError:
        script_rel = here
    try:
        skill_rel = skill_md.relative_to(root.resolve())
    except ValueError:
        skill_rel = skill_md
    return _AGENT_GUIDANCE_TEMPLATE.format(script=script_rel, skill=skill_rel)


def _write_agent_guidance(target: Path, snippet: str) -> None:
    """Append *snippet* to *target*, creating parent dirs and the file if needed."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(snippet)


def _prompt_agent_guidance(root: Path) -> None:
    """Offer to write pyramid guidance into an agent doc file (interactive only)."""
    click.echo("\nNo pyramid guidance found in CLAUDE.md or AGENTS.md.", err=True)
    click.echo("Add it now? Choose a destination file:", err=True)
    for num, rel in _AGENT_DOC_OPTIONS:
        exists_note = " (exists — will append)" if (root / rel).exists() else " (will create)"
        click.echo(f"  {num}. {rel}{exists_note}", err=True)
    click.echo("  s. skip", err=True)

    choice = click.prompt("Choice", default="1", show_default=True, err=True)
    option_map = {num: rel for num, rel in _AGENT_DOC_OPTIONS}
    chosen = option_map.get(choice)
    if not chosen:
        click.echo("Skipped. Add guidance manually before running agents.", err=True)
        return

    target = root / chosen
    _write_agent_guidance(target, _agent_guidance_snippet(root))
    click.echo(f"Added pyramid guidance to {target}", err=True)


# ─────────────────────────────────────────────
# SECTION: CLI commands
# ─────────────────────────────────────────────


@click.group()
@click.version_option("0.2.0")
def cli() -> None:
    """Pyramid Summary Generator — progressive codebase navigation."""


# ── init ──────────────────────────────────────


@cli.command()
@click.option("--db-path", default=None, help="Override .pyramid/ location.")
@click.option(
    "--api",
    default="anthropic",
    type=click.Choice(["anthropic", "openai"]),
    help="LLM provider (default: anthropic).",
)
def init(db_path: str | None, api: str) -> None:
    """Initialize pyramid generator in the current directory."""
    storage = StorageManager(_pyramid_dir(db_path))
    if storage.is_initialized():
        click.echo(f"Already initialized at {storage.pyramid_dir}")
        return
    storage.init(api=api)
    click.echo(f"Initialized pyramid generator at {storage.pyramid_dir}")

    # Prompt to document the skill if no guidance exists yet.
    if not _check_agent_guidance(Path.cwd()):
        if sys.stdin.isatty():
            _prompt_agent_guidance(Path.cwd())
        else:
            click.echo(
                "\nWarning: no pyramid guidance found in CLAUDE.md or AGENTS.md.\n"
                "AI agents won't know to use this skill unless you document it.\n"
                "Run `init` interactively to add it automatically, or add it manually.",
                err=True,
            )

    click.echo("\nNext: uv run pyramid_cli.py analyze .")


# ── analyze ───────────────────────────────────


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--db-path", default=None, help="Override .pyramid/ location.")
@click.option(
    "--api",
    default=None,
    type=click.Choice(["anthropic", "openai"]),
    help="LLM provider override.",
)
@click.option("--model", default=None, help="Override LLM model name.")
@click.option("--force", is_flag=True, help="Re-analyze all files, ignoring cache.")
@click.option("--workers", default=4, show_default=True, help="Parallel LLM workers.")
@click.option("--no-llm", "no_llm", is_flag=True, help="Skip LLM; write placeholder summaries.")
def analyze(
    path: str,
    db_path: str | None,
    api: str | None,
    model: str | None,
    force: bool,
    workers: int,
    no_llm: bool,
) -> None:
    """Analyze a codebase and generate pyramid summaries."""
    root = Path(path).resolve()
    storage = StorageManager(_pyramid_dir(db_path))
    _require_init(storage)

    config = storage.load_config()
    effective_api = api or str(config.get("api", "anthropic"))
    summarizer = Summarizer(api=effective_api, model=model, no_llm=no_llm)
    parser = CodeParser()

    click.echo(f"Analyzing: {root}")
    files = parser.walk_directory(root, root / ".pyramidignore")
    click.echo(f"Source files found: {len(files)}")

    index = storage.load_index()
    pending: list[tuple[Element, str]] = []
    for file_path in files:
        for element in parser.parse_file(file_path, root):
            sha = element.content_hash()
            if not force and sha in index:
                continue
            pending.append((element, sha))

    if not pending:
        click.echo("All files up to date.")
        return

    click.echo(f"Elements to summarize: {len(pending)}")

    provider = summarizer._detect_provider()
    if provider == "stub" and not no_llm:
        click.echo(
            "Warning: no LLM provider configured. Using placeholder summaries.\n"
            "  Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or ensure `claude` is in PATH.",
            err=True,
        )

    def _process(item: tuple[Element, str]) -> tuple[str, dict[str, object]]:
        element, sha = item
        summaries = summarizer.summarize(element, _ANALYZE_LEVELS)
        storage.save_data(sha, {
            "path": element.path,
            "element_type": element.element_type,
            "name": element.name,
            "start_line": element.start_line,
            "end_line": element.end_line,
            "code": element.code,
            "levels": summaries,
        })
        return sha, {
            "path": element.path,
            "element_type": element.element_type,
            "name": element.name,
            "levels": summaries,
        }

    completed = 0
    with click.progressbar(length=len(pending), label="Summarizing") as bar:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process, item): item for item in pending}
            for future in as_completed(futures):
                try:
                    sha, entry = future.result()
                    index[sha] = entry
                    completed += 1
                except (RuntimeError, OSError, ValueError):
                    elem, _ = futures[future]
                    logger.exception("Failed to process %s", elem.path)
                bar.update(1)

    storage.save_index(index)
    click.echo(f"\nDone. Indexed {completed} elements → {storage.pyramid_dir}")


# ── query ─────────────────────────────────────


@cli.command()
@click.argument("query_text")
@click.option(
    "--level",
    default="16",
    type=click.Choice(["4", "8", "16", "32", "64"]),
    help="Summary level to search (default: 16).",
)
@click.option(
    "--type",
    "element_type",
    default=None,
    type=click.Choice(["file", "function", "class"]),
    help="Filter by element type.",
)
@click.option("--db-path", default=None)
@click.option("--limit", default=20, show_default=True, help="Max results.")
def query(
    query_text: str,
    level: str,
    element_type: str | None,
    db_path: str | None,
    limit: int,
) -> None:
    """Search pyramid summaries by keyword."""
    storage = StorageManager(_pyramid_dir(db_path))
    _require_init(storage)

    index = storage.load_index()
    if not index:
        raise click.ClickException("No indexed elements. Run: uv run pyramid_cli.py analyze .")

    needle = query_text.lower()
    results: list[tuple[dict[str, object], str, str]] = []

    for sha, entry in index.items():
        if element_type and entry.get("element_type") != element_type:
            continue
        levels_data = entry.get("levels") or {}
        summary = str(levels_data.get(level, ""))  # type: ignore[union-attr]
        path_str = str(entry.get("path", ""))
        if needle in summary.lower() or needle in path_str.lower():
            results.append((entry, summary, sha))

    if not results:
        click.echo(f"No results for '{query_text}' at level {level}.")
        return

    click.echo(f"{len(results)} result(s) for '{query_text}' (level {level}):\n")
    for entry, summary, _sha in results[:limit]:
        path_str = str(entry.get("path", ""))
        etype = str(entry.get("element_type", "file"))
        name = str(entry.get("name", ""))
        label = path_str if etype == "file" else f"{path_str}::{name}"
        click.echo(f"  {label}  [{etype}]")
        click.echo(f"    {summary}")
        click.echo()

    if len(results) > limit:
        click.echo(f"  … {len(results) - limit} more (use --limit to show more)")


# ── get ───────────────────────────────────────


@cli.command()
@click.argument("element_path")
@click.option(
    "--level",
    default="16",
    type=click.Choice(["4", "8", "16", "32", "64"]),
    help="Summary level (default: 16).",
)
@click.option("--show-code", is_flag=True, help="Print the raw source code.")
@click.option("--db-path", default=None)
@click.option("--api", default=None, type=click.Choice(["anthropic", "openai"]))
@click.option("--model", default=None)
def get(
    element_path: str,
    level: str,
    show_code: bool,
    db_path: str | None,
    api: str | None,
    model: str | None,
) -> None:
    """Get pyramid summary for a specific code element."""
    storage = StorageManager(_pyramid_dir(db_path))
    _require_init(storage)

    index = storage.load_index()
    needle = element_path.lower().replace("\\", "/")
    matches = [
        (sha, entry)
        for sha, entry in index.items()
        if str(entry.get("path", "")).lower().replace("\\", "/").startswith(needle)
    ]

    if not matches:
        raise click.ClickException(
            f"No element found for '{element_path}'.\n"
            "Run `uv run pyramid_cli.py list` to see available paths."
        )

    for sha, entry in matches:
        path_str = str(entry.get("path", ""))
        name = str(entry.get("name", ""))
        etype = str(entry.get("element_type", "file"))
        label = path_str if etype == "file" else f"{path_str}::{name}"

        # Fast path: level in index (4/8/16)
        levels_data = entry.get("levels") or {}
        summary = str(levels_data.get(level, ""))  # type: ignore[union-attr]

        if not summary:
            # Slow path: check or generate in data/<sha>.json
            data = storage.load_data(sha)
            if data is None:
                raise click.ClickException(
                    f"Data file missing for '{path_str}'. Re-run analyze."
                )
            data_levels: dict[str, str] = dict(data.get("levels") or {})  # type: ignore[arg-type]
            summary = data_levels.get(level, "")

            if not summary:
                # Fill every missing level in sequence from the lowest gap up to
                # the requested level, so the prefix chain is never broken.
                # Example: target=32, stored={4,8,16} → generate only 32
                # Example: target=32, stored={4}      → generate 8, 16, 32 in order
                target = int(level)
                target_idx = LEVEL_SEQUENCE.index(target)
                to_generate = [
                    lv for lv in LEVEL_SEQUENCE[: target_idx + 1]
                    if str(lv) not in data_levels
                ]

                config = storage.load_config()
                effective_api = api or str(config.get("api", "anthropic"))
                summarizer = Summarizer(api=effective_api, model=model)
                element = Element(
                    path=path_str,
                    element_type=etype,
                    name=name,
                    code=str(data.get("code", "")),
                    start_line=int(data.get("start_line", 1)),  # type: ignore[arg-type]
                    end_line=int(data.get("end_line", 1)),  # type: ignore[arg-type]
                )

                # Seed = highest stored level below the first gap
                first_missing = to_generate[0]
                available_below = [
                    lv for lv in LEVEL_SEQUENCE
                    if lv < first_missing and str(lv) in data_levels
                ]
                cur_seed_level: int | None = max(available_below) if available_below else None
                cur_seed: str | None = (
                    data_levels[str(cur_seed_level)] if cur_seed_level else None
                )

                click.echo(
                    f"Generating level(s) {to_generate} for '{label}'…", err=True
                )
                for gen_level in to_generate:
                    result = summarizer.summarize(
                        element,
                        (gen_level,),
                        seed=cur_seed,
                        seed_level=cur_seed_level,
                    )
                    generated = result.get(str(gen_level), f"{etype} {name}")
                    data_levels[str(gen_level)] = generated
                    cur_seed_level = gen_level
                    cur_seed = generated

                storage.save_data(sha, {**data, "levels": data_levels})  # type: ignore[arg-type]
                summary = data_levels.get(level, "")

        click.echo(f"{label}  (level {level})")
        click.echo(f"  {summary}")

        if show_code:
            data = storage.load_data(sha)
            code = str(data.get("code", "")) if data else ""
            if code:
                click.echo()
                click.echo("─" * 72)
                click.echo(code)
                click.echo("─" * 72)
        click.echo()


# ── list ──────────────────────────────────────


@cli.command("list")
@click.option(
    "--level",
    default="4",
    type=click.Choice(["4", "8", "16"]),
    help="Summary level (default: 4).",
)
@click.option(
    "--type",
    "element_type",
    default="file",
    type=click.Choice(["file", "function", "class", "all"]),
    help="Filter by element type (default: file).",
)
@click.option("--db-path", default=None)
def list_cmd(level: str, element_type: str, db_path: str | None) -> None:
    """List indexed code elements with their summaries."""
    storage = StorageManager(_pyramid_dir(db_path))
    _require_init(storage)

    index = storage.load_index()
    if not index:
        raise click.ClickException("No indexed elements. Run: uv run pyramid_cli.py analyze .")

    rows: dict[str, tuple[str, str]] = {}
    for _sha, entry in index.items():
        etype = str(entry.get("element_type", "file"))
        if element_type != "all" and etype != element_type:
            continue
        path_str = str(entry.get("path", ""))
        name = str(entry.get("name", ""))
        levels_data = entry.get("levels") or {}
        summary = str(levels_data.get(level, ""))  # type: ignore[union-attr]
        label = path_str if etype == "file" else f"{path_str}::{name}"
        rows[label] = (summary, etype)

    if not rows:
        click.echo(f"No {element_type} elements found.")
        return

    click.echo(f"{element_type.capitalize()} elements ({len(rows)} total):\n")
    for label, (summary, _etype) in sorted(rows.items()):
        click.echo(f"  {label}")
        if summary:
            click.echo(f"    {summary}")
        click.echo()


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    cli()
