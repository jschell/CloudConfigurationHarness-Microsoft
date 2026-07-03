"""Regression-check every rule/fixture pair in the journal for real,
in parallel. Promotes the ad-hoc snippet from
docs/operating-tiers.md's "Regression-check the whole rule set for
real" section into a reusable tool.

Safe to parallelize (unlike pattern_extract/rule_compile/
fixture_generate against the shared journal -- see
docs/plans/active/2026-07-02-tier-2-storage-buildout.md's Task 4):
this tool only reads the journal, and each check_id's work (compile
its own fixtures, run conftest against its own rule) touches only
files scoped to that check_id, so there's nothing for two workers to
race on. Threads, not processes, since the work is I/O-bound
(waiting on az/conftest subprocesses), not CPU-bound.

Scoped to --policy-dir by rule_path prefix, not just used for conftest's
--policy flag: a journal can hold multiple resource types' rules (e.g.
Storage and KeyVault sharing one journal across git worktrees per
docs/onboarding-new-resource-type.md), and each worktree only has the
fixture/rule *files* for its own resource type on disk -- querying every
rule_path regardless of --policy-dir would try to bicep-compile fixture
files that don't exist in the current worktree and report them as false
failures.

Usage:
    python -m harness.tools.regression_check
    python -m harness.tools.regression_check --policy-dir rules/azure/keyvault --workers 8
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from harness.adapters import bicep_validate, rego_validate
from harness.journal.db import connect

DEFAULT_WORKERS = 8


def _check_one(
    check_id: str, fixture_path: str, variants_json: str | None, policy_dir: Path
) -> list[dict[str, Any]]:
    fixture_dir = Path(fixture_path)
    variants = (
        json.loads(variants_json)
        if variants_json
        else [
            {"label": "vulnerable", "expected_verdict": "fail"},
            {"label": "safe", "expected_verdict": "pass"},
        ]
    )
    results = []
    for v in variants:
        label, expected = v["label"], v["expected_verdict"]
        json_path = fixture_dir / f"{label}.json"
        bicep_validate.bicep_to_json(fixture_dir / f"{label}.bicep", json_path)
        result = rego_validate.validate(json_path, policy_dir, expected, check_id)
        results.append({"check_id": check_id, "label": label, **result})
    return results


def run(db_path: Path | str | None, policy_dir: Path, workers: int) -> bool:
    conn = connect(db_path) if db_path else connect()
    rows = conn.execute(
        """SELECT r.check_id, f.fixture_path, f.variants_json
           FROM rules r JOIN fixtures f ON r.check_id = f.check_id
           WHERE r.rule_path LIKE ?
           ORDER BY r.check_id""",
        (f"{policy_dir.as_posix()}%",),
    ).fetchall()
    print(f"checking {len(rows)} rules under {policy_dir} with {workers} workers")

    all_ok = True
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _check_one,
                r["check_id"],
                r["fixture_path"],
                r["variants_json"],
                policy_dir,
            ): r["check_id"]
            for r in rows
        }
        for future in as_completed(futures):
            check_id = futures[future]
            try:
                results = future.result()
            except Exception as exc:  # noqa: BLE001 -- surface any adapter error per check_id
                print(f"{check_id}: ERROR {exc}")
                all_ok = False
                continue
            for result in results:
                if not result["passed"]:
                    all_ok = False
                    print(f"{result['check_id']} {result['label']} -> FAIL {result}")

    print("ALL PASSED" if all_ok else "SOME FAILED")
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--policy-dir", type=Path, default=Path("rules/azure/storage"))
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    ok = run(args.db, args.policy_dir, args.workers)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
