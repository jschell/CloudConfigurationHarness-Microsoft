"""Preflight requirement checks for the FSM runner.

Task 5's verification run silently stubbed `az bicep build` when the tool
was missing from the sandbox. That made a stub indistinguishable from a
real pass in the journal. This module turns "tool is missing" into a hard,
clearly-labeled failure instead: workflow states declare which external
tools/keys they need (`requires:` in the workflow YAML), and the runner
checks them before invoking the adapter/LLM call, raising WorkflowError
with an actionable install hint rather than proceeding on a stub.

Usage as a standalone check (prints a status table, exit 1 if anything
required by the given workflow -- or everything known, with no args -- is
missing):

    python -m harness.engine.preflight [workflow.yaml ...]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ENGINE_DIR = Path(__file__).parent
ENV_PATH = ENGINE_DIR / ".env"


@dataclass
class Requirement:
    name: str
    ok: bool
    detail: str
    install_hint: str


def _which_ok(binary: str) -> tuple[bool, str]:
    path = shutil.which(binary)
    if not path:
        return False, f"'{binary}' not found on PATH"
    return True, f"found at {path}"


def _env_file_values() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    values = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def check_az() -> Requirement:
    ok, detail = _which_ok("az")
    if ok:
        # `az bicep build` needs the bicep component installed, not just the
        # CLI. Use the resolved path (not the bare "az") -- on Windows it's
        # a .cmd shim, and subprocess.run(list_form) doesn't apply PATHEXT
        # resolution the way a shell does.
        result = subprocess.run(
            [shutil.which("az") or "az", "bicep", "version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            ok = False
            detail = (
                f"'az' found but 'az bicep version' failed: {result.stderr.strip()}"
            )
    return Requirement(
        name="az",
        ok=ok,
        detail=detail,
        install_hint="choco install azure-cli -y ; az bicep install",
    )


def check_conftest() -> Requirement:
    ok, detail = _which_ok("conftest")
    return Requirement(
        name="conftest",
        ok=ok,
        detail=detail,
        install_hint="choco install conftest -y",
    )


def check_opa() -> Requirement:
    ok, detail = _which_ok("opa")
    return Requirement(
        name="opa",
        ok=ok,
        detail=detail,
        install_hint="choco install opa -y",
    )


def check_claude_cli() -> Requirement:
    ok, detail = _which_ok("claude")
    return Requirement(
        name="claude_cli",
        ok=ok,
        detail=detail,
        install_hint="npm install -g @anthropic-ai/claude-code",
    )


def check_zai_key() -> Requirement:
    values = _env_file_values()
    ok = bool(values.get("EXECUTOR_GLM_ANTHROPIC_API_KEY"))
    detail = (
        "EXECUTOR_GLM_ANTHROPIC_API_KEY set in harness/engine/.env"
        if ok
        else "EXECUTOR_GLM_ANTHROPIC_API_KEY missing from harness/engine/.env"
    )
    return Requirement(
        name="zai_key",
        ok=ok,
        detail=detail,
        install_hint=(
            "add EXECUTOR_GLM_ANTHROPIC_API_KEY=<your Z.ai API key> to "
            "harness/engine/.env (gitignored)"
        ),
    )


ALL_CHECKS = {
    "az": check_az,
    "conftest": check_conftest,
    "opa": check_opa,
    "claude_cli": check_claude_cli,
    "zai_key": check_zai_key,
}


def check(names: list[str]) -> list[Requirement]:
    return [ALL_CHECKS[name]() for name in names]


def require(names: list[str]) -> None:
    """Raise RuntimeError listing every unmet requirement in `names`.
    Called by the runner before an adapter/LLM state that declared
    `requires:` in its workflow YAML -- never silently substitutes a stub."""
    failures = [r for r in check(names) if not r.ok]
    if failures:
        lines = [
            f"  - {r.name}: {r.detail} (install: {r.install_hint})" for r in failures
        ]
        raise RuntimeError(
            "preflight requirement(s) not met, refusing to fake a result:\n"
            + "\n".join(lines)
        )


def _print_report(requirements: list[Requirement]) -> bool:
    all_ok = True
    for r in requirements:
        status = "OK  " if r.ok else "MISS"
        print(f"[{status}] {r.name}: {r.detail}")
        if not r.ok:
            all_ok = False
            print(f"        install: {r.install_hint}")
    return all_ok


def main() -> int:
    import yaml

    names: set[str] = set()
    workflow_paths = sys.argv[1:]
    if workflow_paths:
        for wf_path in workflow_paths:
            workflow = yaml.safe_load(Path(wf_path).read_text())
            for state in workflow.get("states", []):
                names.update(state.get("requires", []))
    else:
        names = set(ALL_CHECKS)

    if not names:
        print("no 'requires' declared by given workflow(s); nothing to check")
        return 0

    requirements = check(sorted(names))
    all_ok = _print_report(requirements)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
