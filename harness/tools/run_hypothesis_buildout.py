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

Generic across resource types (see docs/onboarding-new-resource-type.md):
`hypotheses` is a shared table tagged with `resource_type`, so this only
ever processes hypotheses matching the given workflow's own
resource_config.resource_type -- a second resource type's hypotheses
sitting in the same journal are never touched by the wrong workflow.

Usage:
    python -m harness.tools.run_hypothesis_buildout
    python -m harness.tools.run_hypothesis_buildout --workflow harness/workflows/vm-atomic-tier.yaml
    python -m harness.tools.run_hypothesis_buildout --role-override executor_glm=executor_claude
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from harness.engine.runner import Runner, WorkflowError, load_workflow

DEFAULT_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1] / "workflows" / "storage-atomic-tier.yaml"
)
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 15


def remaining_hypothesis_ids(conn, resource_type: str, tier: int) -> list[int]:
    compiled = {
        r["hypothesis_id"] for r in conn.execute("SELECT hypothesis_id FROM rules")
    }
    return [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM hypotheses WHERE resource_type = ? AND tier = ? ORDER BY id",
            (resource_type, tier),
        ).fetchall()
        if r["id"] not in compiled
    ]


def run(
    workflow_path: Path,
    db_path=None,
    role_override: dict[str, str] | None = None,
) -> dict[int, str]:
    workflow = load_workflow(workflow_path)
    resource_type = workflow["resource_config"]["resource_type"]
    tier = workflow["resource_config"]["tier"]

    runner = Runner(db_path=db_path, role_override=role_override or {})
    conn = runner.conn
    ids = remaining_hypothesis_ids(conn, resource_type, tier)
    print(
        f"{len(ids)} tier-{tier} hypotheses remaining to compile for "
        f"{resource_type}: {ids}"
    )

    results: dict[int, str] = {}
    for hypothesis_id in ids:
        print(f"=== hypothesis {hypothesis_id} ===")
        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                runner.start(
                    workflow_path,
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
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW_PATH)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument(
        "--role-override",
        action="append",
        default=[],
        help="workflow_role=roles_yaml_role, e.g. executor_glm=executor_claude (repeatable)",
    )
    args = parser.parse_args()
    role_override = dict(pair.split("=", 1) for pair in args.role_override)

    results = run(args.workflow, db_path=args.db, role_override=role_override)
    print("\n=== summary ===")
    for hypothesis_id, outcome in results.items():
        print(f"hypothesis {hypothesis_id}: {outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
