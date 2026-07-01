"""Deterministic Rego adapter.

Wraps `conftest test <fixture>.json --policy rules/azure/storage/` to
produce the actual pass/fail security verdict for a fixture. Rego
evaluates JSON, not Bicep, so fixtures are validated as their compiled
ARM-export-shaped JSON (see bicep_validate.bicep_to_json for the
conversion step).

Interface (shared with bicep_validate.py):
    Input: fixture JSON file path, expected verdict ("pass" | "fail")
    Output: dict matching the `runs` table shape:
        {adapter, check_id, fixture_path, expected_verdict, actual_verdict,
         passed: bool, raw_output: str}

Verdict semantics: expected_verdict/actual_verdict describe whether the
fixture is flagged as vulnerable ("fail") or safe ("pass") by the policy
under test -- i.e. whether any `deny` rule fired.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ADAPTER_NAME = "rego_validate"


def validate(
    fixture_json_path: str | Path,
    policy_dir: str | Path,
    expected_verdict: str,
    check_id: str,
) -> dict:
    fixture_json_path = Path(fixture_json_path)
    result = subprocess.run(
        [
            "conftest",
            "test",
            str(fixture_json_path),
            "--policy",
            str(policy_dir),
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )

    raw_output = result.stdout or result.stderr

    try:
        parsed = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "adapter": ADAPTER_NAME,
            "check_id": check_id,
            "fixture_path": str(fixture_json_path),
            "expected_verdict": expected_verdict,
            "actual_verdict": "error",
            "passed": False,
            "raw_output": f"could not parse conftest output: {exc}\n{raw_output}",
        }

    failures = sum(len(file_result.get("failures", []) or []) for file_result in parsed)
    actual_verdict = "fail" if failures > 0 else "pass"

    return {
        "adapter": ADAPTER_NAME,
        "check_id": check_id,
        "fixture_path": str(fixture_json_path),
        "expected_verdict": expected_verdict,
        "actual_verdict": actual_verdict,
        "passed": actual_verdict == expected_verdict,
        "raw_output": raw_output,
    }
