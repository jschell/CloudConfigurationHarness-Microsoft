"""Batch driver: compile+validate a rule for every hypothesis that
doesn't have one yet, one at a time, through the normal FSM
(rule_compile -> fixture_generate -> fixture_validate -> gate).

Complements harness.tools.run_schema_coverage, which fills
schema_coverage/hypotheses -- this is the next stage, turning discovered
hypotheses into validated (or legitimately rejected) rules. Runs
sequentially so a failure on one hypothesis doesn't stop the rest.
"rejected after 3 attempts" from the FSM's own gate logic is a normal,
non-exceptional outcome (some hypotheses won't compile to a good atomic
check, and that's the harness working as designed) -- this driver's own
retry-with-backoff is for a different failure class: transient
infrastructure errors (API overload, timeouts) that abort the run before
the gate ever gets a verdict.

Usage:
    python -m harness.tools.run_hypothesis_buildout
    python -m harness.tools.run_hypothesis_buildout --role-override executor_glm=executor_claude
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from harness.engine.runner import Runner, WorkflowError

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "workflows" / "storage-atomic-tier.yaml"
)
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 15


def remaining_hypothesis_ids(conn) -> list[int]:
    compiled = {
        r["hypothesis_id"] for r in conn.execute("SELECT hypothesis_id FROM rules")
    }
    return [
        r["id"]
        for r in conn.execute("SELECT id FROM hypotheses ORDER BY id").fetchall()
        if r["id"] not in compiled
    ]


def run(db_path=None, role_override: dict[str, str] | None = None) -> dict[int, str]:
    runner = Runner(db_path=db_path, role_override=role_override or {})
    conn = runner.conn
    ids = remaining_hypothesis_ids(conn)
    print(f"{len(ids)} hypotheses remaining to compile: {ids}")

    results: dict[int, str] = {}
    for hypothesis_id in ids:
        print(f"=== hypothesis {hypothesis_id} ===")
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                runner.start(
                    WORKFLOW_PATH,
                    start_state="rule_compile",
                    initial_context={"target_hypothesis_id": hypothesis_id},
                )
                last_error = None
                break
            except (WorkflowError, subprocess.TimeoutExpired) as exc:
                last_error = exc
                print(f"  attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS)

        if last_error is not None:
            results[hypothesis_id] = (
                f"infra error after {MAX_ATTEMPTS} attempts: {last_error}"
            )
            print(f"  {results[hypothesis_id]}")
            continue

        rule_row = conn.execute(
            "SELECT status, check_id FROM rules WHERE hypothesis_id = ?",
            (hypothesis_id,),
        ).fetchone()
        if rule_row:
            results[hypothesis_id] = f"{rule_row['check_id']}: {rule_row['status']}"
        else:
            results[hypothesis_id] = "no rule row written"
        print(f"  {results[hypothesis_id]}")

    # Housekeeping: any workflow_runs row still 'running' at this point
    # belongs to an attempt that raised before completing -- mark it
    # failed so a future --resume doesn't pick up a stale, abandoned run.
    conn.execute("UPDATE workflow_runs SET status = 'failed' WHERE status = 'running'")
    conn.commit()

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument(
        "--role-override",
        action="append",
        default=[],
        help="workflow_role=roles_yaml_role, e.g. executor_glm=executor_claude (repeatable)",
    )
    args = parser.parse_args()
    role_override = dict(pair.split("=", 1) for pair in args.role_override)

    results = run(db_path=args.db, role_override=role_override)
    print("\n=== summary ===")
    for hypothesis_id, outcome in results.items():
        print(f"hypothesis {hypothesis_id}: {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
