"""Deterministic Bicep/ARM schema adapter.

Wraps `az bicep build` (schema/syntax conformance) and, when a sandbox
resource group is configured, `az deployment group validate` (deployability).
This adapter never produces a security verdict -- it only confirms a
fixture is well-formed. A fixture that fails to compile is a fixture bug,
not a rule result, so compile failures are surfaced as actual_verdict
"error" rather than "fail" to keep them distinguishable from a real policy
verdict downstream (see rego_validate.py for the actual pass/fail verdict).

Interface (shared with rego_validate.py):
    Input: fixture file path, expected verdict ("pass" | "fail")
    Output: dict matching the `runs` table shape:
        {adapter, check_id, fixture_path, expected_verdict, actual_verdict,
         passed: bool, raw_output: str}
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ADAPTER_NAME = "bicep_validate"


def validate(
    fixture_path: str | Path,
    expected_verdict: str,
    check_id: str,
    deployment_group: str | None = None,
) -> dict:
    """Confirm a .bicep fixture compiles (and optionally deploy-validates).

    expected_verdict here means "expected to compile cleanly" -- this
    adapter is a schema-conformance gate, not a security check, so
    expected_verdict should normally be "pass" for every fixture regardless
    of whether the fixture is the vulnerable or safe variant.
    """
    fixture_path = Path(fixture_path)
    build = subprocess.run(
        ["az", "bicep", "build", "--file", str(fixture_path), "--stdout"],
        capture_output=True,
        text=True,
    )

    if build.returncode != 0:
        return {
            "adapter": ADAPTER_NAME,
            "check_id": check_id,
            "fixture_path": str(fixture_path),
            "expected_verdict": expected_verdict,
            "actual_verdict": "error",  # compile failure: fixture bug, not a security verdict
            "passed": False,
            "raw_output": build.stderr,
        }

    raw_output = build.stdout
    actual_verdict = "pass"

    if deployment_group:
        deploy = subprocess.run(
            [
                "az",
                "deployment",
                "group",
                "validate",
                "--resource-group",
                deployment_group,
                "--template-file",
                str(fixture_path),
            ],
            capture_output=True,
            text=True,
        )
        raw_output += "\n" + deploy.stdout + deploy.stderr
        actual_verdict = "pass" if deploy.returncode == 0 else "error"

    return {
        "adapter": ADAPTER_NAME,
        "check_id": check_id,
        "fixture_path": str(fixture_path),
        "expected_verdict": expected_verdict,
        "actual_verdict": actual_verdict,
        "passed": actual_verdict == expected_verdict,
        "raw_output": raw_output,
    }


def bicep_to_json(fixture_path: str | Path, out_path: str | Path) -> Path:
    """Compile a .bicep fixture to its ARM-export-shaped JSON, for the Rego
    adapter (Rego evaluates JSON, not Bicep). Raises on compile failure --
    callers should treat that as a fixture bug, same as validate() above."""
    fixture_path = Path(fixture_path)
    out_path = Path(out_path)
    result = subprocess.run(
        [
            "az",
            "bicep",
            "build",
            "--file",
            str(fixture_path),
            "--outfile",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bicep compile failed for {fixture_path}: {result.stderr}")
    return out_path
