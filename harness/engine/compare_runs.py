"""A/B comparison report for two workflow_runs of the same FSM workflow.

Intended use (Task 7): run `storage-atomic-tier.yaml` twice -- once with
`rule_compile`/`fixture_generate` pinned to executor_claude (the default
role mapping) and once with `--role-override executor_claude=executor_glm`
-- then diff the two runs to see whether the two models produced
equivalent rules/fixtures, in how many attempts, and whether both passed
the same deterministic adapter verdicts.

Each workflow_runs row's context_json carries a `_model_map` (state name ->
{declared_role, resolved_role, model}) recorded by Runner.start(), so this
script can attribute results to a model without needing roles.yaml to have
stayed unchanged between the two runs.

Usage:
    python -m harness.engine.compare_runs --run-a 1 --run-b 2
    python -m harness.engine.compare_runs --run-a 1 --db-a a.db --run-b 1 --db-b b.db
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

from harness.journal.db import connect

REPO_ROOT = Path(__file__).resolve().parents[2]


class CompareError(RuntimeError):
    pass


def _load_run(conn, run_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise CompareError(f"no workflow_runs row with id={run_id}")
    context = json.loads(row["context_json"] or "{}")
    check_id = context.get("check_id")

    rule = None
    fixture = None
    runs = []
    if check_id:
        rule_row = conn.execute(
            "SELECT * FROM rules WHERE check_id = ?", (check_id,)
        ).fetchone()
        rule = dict(rule_row) if rule_row else None
        fixture_row = conn.execute(
            "SELECT * FROM fixtures WHERE check_id = ?", (check_id,)
        ).fetchone()
        fixture = dict(fixture_row) if fixture_row else None
        runs = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM runs WHERE check_id = ? ORDER BY id", (check_id,)
            ).fetchall()
        ]

    return {
        "run_id": run_id,
        "workflow_name": row["workflow_name"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "check_id": check_id,
        "model_map": context.get("_model_map", {}),
        "retries": context.get("retries", {}).get(check_id, 0) if check_id else 0,
        "last_failure_reason": context.get("last_failure_reason"),
        "rule": rule,
        "fixture": fixture,
        "runs": runs,
    }


def _rego_diff(rule_a: dict | None, rule_b: dict | None) -> str:
    if not rule_a or not rule_b:
        return "(one or both runs produced no rule -- nothing to diff)"
    path_a = REPO_ROOT / rule_a["rule_path"]
    path_b = REPO_ROOT / rule_b["rule_path"]
    if not path_a.exists() or not path_b.exists():
        return "(rule file missing on disk -- nothing to diff)"
    if path_a == path_b:
        return "(both runs wrote the same rule_path -- run B overwrote run A's file; diff not meaningful, compare journal history instead)"
    text_a = path_a.read_text().splitlines(keepends=True)
    text_b = path_b.read_text().splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            text_a,
            text_b,
            fromfile=str(rule_a["rule_path"]),
            tofile=str(rule_b["rule_path"]),
        )
    )
    return "".join(diff) if diff else "(rule content is identical)"


def _adapter_summary(runs: list[dict]) -> str:
    if not runs:
        return "(no adapter runs recorded)"
    lines = []
    for r in runs:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(
            f"  [{mark}] {r['adapter']} expected={r['expected_verdict']} actual={r['actual_verdict']}"
        )
    return "\n".join(lines)


def compare(run_a: dict[str, Any], run_b: dict[str, Any]) -> str:
    lines = ["# A/B run comparison", ""]

    for label, run in (("A", run_a), ("B", run_b)):
        models_used = {v["model"] for v in run["model_map"].values()}
        lines.append(f"## Run {label} (workflow_runs.id={run['run_id']})")
        lines.append(f"- workflow: {run['workflow_name']}")
        lines.append(
            f"- status: {run['status']}  ({run['created_at']} -> {run['updated_at']})"
        )
        lines.append(
            f"- models used: {', '.join(sorted(models_used)) or '(none recorded)'}"
        )
        lines.append(f"- check_id: {run['check_id'] or '(none produced)'}")
        lines.append(
            f"- rule status: {run['rule']['status'] if run['rule'] else '(no rule)'}"
        )
        lines.append(f"- retries before terminal state: {run['retries']}")
        if run["last_failure_reason"]:
            lines.append(f"- last failure reason: {run['last_failure_reason']}")
        lines.append("- adapter verdicts:")
        lines.append(_adapter_summary(run["runs"]))
        lines.append("")

    lines.append("## Verdict agreement")
    a_ok = run_a["rule"]["status"] == "validated" if run_a["rule"] else False
    b_ok = run_b["rule"]["status"] == "validated" if run_b["rule"] else False
    if a_ok == b_ok:
        lines.append(
            f"Both runs reached the same outcome: {'validated' if a_ok else 'not validated'}."
        )
    else:
        lines.append(
            f"DISAGREEMENT: run A {'validated' if a_ok else 'did not validate'}, "
            f"run B {'validated' if b_ok else 'did not validate'}."
        )
    lines.append("")

    lines.append("## Rego rule diff (A -> B)")
    lines.append("```diff")
    lines.append(_rego_diff(run_a["rule"], run_b["rule"]))
    lines.append("```")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two workflow_runs (A/B model comparison)."
    )
    parser.add_argument("--run-a", type=int, required=True)
    parser.add_argument("--run-b", type=int, required=True)
    parser.add_argument("--db-a", type=Path, default=None)
    parser.add_argument("--db-b", type=Path, default=None)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write report to this file instead of stdout",
    )
    args = parser.parse_args()

    conn_a = connect(args.db_a) if args.db_a else connect()
    conn_b = connect(args.db_b) if args.db_b else conn_a

    run_a = _load_run(conn_a, args.run_a)
    run_b = _load_run(conn_b, args.run_b)

    report = compare(run_a, run_b)
    if args.out:
        args.out.write_text(report)
        print(f"wrote comparison report to {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
