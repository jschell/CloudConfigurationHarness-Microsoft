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

Rule/fixture content comes from `rule_history`/`fixture_history` (append-only,
tagged with workflow_run_id -- see schema.sql), not the live `rules`/
`fixtures` rows or files on disk. Those are mutable single-row-per-check_id,
so if two runs are A/B'd against the same check_id (the common case here --
same hypothesis, two models), whichever ran last overwrites the other; the
history tables are what let this script recover exactly what each run
actually produced regardless of what a later run did to the same check_id.

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


class CompareError(RuntimeError):
    pass


def _load_run(conn, run_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise CompareError(f"no workflow_runs row with id={run_id}")
    context = json.loads(row["context_json"] or "{}")
    check_id = context.get("check_id")

    rule_history = None
    fixture_history = None
    runs = []
    if check_id:
        rule_history_row = conn.execute(
            "SELECT * FROM rule_history WHERE workflow_run_id = ? AND check_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (run_id, check_id),
        ).fetchone()
        rule_history = dict(rule_history_row) if rule_history_row else None
        fixture_history_row = conn.execute(
            "SELECT * FROM fixture_history WHERE workflow_run_id = ? AND check_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (run_id, check_id),
        ).fetchone()
        fixture_history = dict(fixture_history_row) if fixture_history_row else None
        # `runs` is append-only and timestamped (no workflow_run_id column,
        # predates it), so it's scoped to this run's own
        # [created_at, updated_at] window to avoid attributing another
        # run's adapter verdicts to this one when check_ids collide.
        runs = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM runs WHERE check_id = ? AND run_at >= ? AND run_at <= ? "
                "ORDER BY id",
                (check_id, row["created_at"], row["updated_at"]),
            ).fetchall()
        ]

    validated = len(runs) == 2 and all(r["passed"] for r in runs)

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
        "rule_history": rule_history,
        "fixture_history": fixture_history,
        "runs": runs,
        "validated": validated,
    }


def _rego_diff(rule_a: dict | None, rule_b: dict | None) -> str:
    if not rule_a or not rule_b:
        return "(one or both runs produced no rule -- nothing to diff)"
    text_a = rule_a["rego_content"].splitlines(keepends=True)
    text_b = rule_b["rego_content"].splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            text_a,
            text_b,
            fromfile=f"run A: {rule_a['rule_path']}",
            tofile=f"run B: {rule_b['rule_path']}",
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
        lines.append(f"- validated (this run's own adapter checks): {run['validated']}")
        lines.append(f"- retries before terminal state: {run['retries']}")
        if run["last_failure_reason"]:
            lines.append(f"- last failure reason: {run['last_failure_reason']}")
        lines.append("- adapter verdicts:")
        lines.append(_adapter_summary(run["runs"]))
        lines.append("")

    lines.append("## Verdict agreement")
    a_ok, b_ok = run_a["validated"], run_b["validated"]
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
    lines.append(_rego_diff(run_a["rule_history"], run_b["rule_history"]))
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
