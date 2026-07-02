#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""pyramid-setup.py — Install dependencies and initialize pyramid_cli.

Usage:
    uv run pyramid-setup.py              # check deps + init
    uv run pyramid-setup.py --analyze    # check deps + init + analyze current dir
    uv run pyramid-setup.py --analyze PATH
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPT_NAME = "pyramid_cli.py"

_REQUIRED: list[tuple[str, str]] = [
    # (import_name, pip_name)
    ("click", "click>=8.0"),
    ("anthropic", "anthropic>=0.40"),
]
_OPTIONAL: list[tuple[str, str, str]] = [
    # (import_name, pip_name, reason)
    ("tree_sitter_language_pack", "tree-sitter-language-pack", "multi-language parsing (165+ langs incl. PowerShell)"),
]


def _importable(name: str) -> bool:
    """Return True if *name* can be imported without error."""
    result = subprocess.run(
        [sys.executable, "-c", f"import {name}"],
        capture_output=True,
    )
    return result.returncode == 0


def _uv_add(pip_name: str) -> bool:
    """Install a package with `uv add`. Returns True on success."""
    result = subprocess.run(["uv", "add", pip_name], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Warning: uv add {pip_name} failed:\n  {result.stderr.strip()}")
        return False
    return True


def ensure_dependencies() -> None:
    """Ensure all required packages are present, install via uv if not."""
    missing = [
        (import_name, pip_name)
        for import_name, pip_name in _REQUIRED
        if not _importable(import_name)
    ]

    if missing:
        print(f"Installing {len(missing)} required package(s) via uv…")
        for import_name, pip_name in missing:
            print(f"  uv add {pip_name}… ", end="", flush=True)
            if _uv_add(pip_name):
                print("OK")
            else:
                sys.exit(f"Failed to install {pip_name}. Try manually: uv add {pip_name}")
    else:
        print("Required packages: OK")

    for import_name, pip_name, reason in _OPTIONAL:
        if not _importable(import_name):
            print(f"Optional ({reason}): uv add {pip_name}")


def find_cli_script() -> Path:
    """Locate pyramid_cli.py relative to this script."""
    candidate = Path(__file__).parent / _SCRIPT_NAME
    if candidate.exists():
        return candidate
    sys.exit(
        f"Error: {_SCRIPT_NAME} not found in {Path(__file__).parent}\n"
        "Ensure pyramid_cli.py is in the same directory as this script."
    )


def run_cli(cli_script: Path, args: list[str]) -> int:
    """Run pyramid_cli.py with the given arguments via uv."""
    result = subprocess.run(["uv", "run", str(cli_script), *args])
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up pyramid-cli for codebase navigation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run pyramid-setup.py                 # init only
  uv run pyramid-setup.py --analyze       # init + analyze current dir
  uv run pyramid-setup.py --analyze src/  # init + analyze src/
        """,
    )
    parser.add_argument(
        "--analyze",
        nargs="?",
        const=".",
        metavar="PATH",
        help="Run pyramid analyze after init (default: current directory).",
    )
    parser.add_argument(
        "--api",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic).",
    )
    args = parser.parse_args()

    cli_script = find_cli_script()
    cwd = Path.cwd()

    print("=== Pyramid CLI Setup ===\n")

    print("Checking dependencies…")
    ensure_dependencies()
    print()

    pyramid_dir = cwd / ".pyramid"
    if pyramid_dir.exists():
        print(f"Already initialized ({pyramid_dir} exists).")
    else:
        print(f"Initializing in {cwd}…")
        if run_cli(cli_script, ["init", "--api", args.api]) != 0:
            sys.exit("pyramid init failed.")

    print()

    if args.analyze is not None:
        analyze_path = Path(args.analyze).resolve()
        if not analyze_path.exists():
            sys.exit(f"Error: path does not exist: {analyze_path}")
        print(f"Analyzing {analyze_path}…")
        if run_cli(cli_script, ["analyze", str(analyze_path)]) != 0:
            sys.exit("pyramid analyze failed.")
    else:
        print("Next steps:")
        print(f"  uv run {cli_script.name} analyze .")
        print(f"  uv run {cli_script.name} list --level 4")
        print(f"  uv run {cli_script.name} query 'TOPIC' --level 8")

    print("\nDone.")


if __name__ == "__main__":
    main()
