"""Batched driver to classify every remaining property in an enumerated
list for security relevance -- the "sweep to completion" half of
docs/patterns/schema-coverage-discovery.md.

Deliberately outside the FSM (like enumerate_schema_properties.py and
coverage_status.py): this is a maintenance/completion sweep, not a
per-hypothesis discovery-and-validate cycle, and it needs its own retry
loop over small batches rather than one call over the whole remaining
list. A single call covering everything remaining is fragile in
practice -- it hit both a transient 529 (Anthropic overloaded) and a
subprocess timeout in the same session this was built, and a large batch
also means a big prompt and a slow, opaque, hard-to-resume call. Small
batches are cheap to retry individually and never lose already-committed
progress (each batch's `schema_coverage` inserts commit before the next
batch starts).

Usage:
    python -m harness.tools.run_schema_coverage \
        sources/azure/storage/storage-account-properties.enumerated.json \
        "Microsoft.Storage/storageAccounts" \
        --extra-file sources/azure/storage/swagger-refs.md \
        --batch-size 20
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from harness.engine.handlers import _extract_json, apply_schema_classifications
from harness.engine.runner import WorkflowError, _invoke_claude, load_roles
from harness.journal.db import connect

PROMPT_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "workflows"
    / "prompts"
    / "schema_coverage_batch.md"
)
MAX_ATTEMPTS_PER_BATCH = 3
RETRY_BACKOFF_SECONDS = 15


def _remaining_properties(
    conn, enumerated: dict[str, Any], resource_type: str
) -> list[dict[str, Any]]:
    covered = {
        r["property_path"]
        for r in conn.execute(
            "SELECT property_path FROM schema_coverage WHERE resource_type = ?",
            (resource_type,),
        ).fetchall()
    }
    return [p for p in enumerated["properties"] if p["property_path"] not in covered]


def _render_batch_prompt(
    resource_type: str, batch: list[dict[str, Any]], extra_files: dict[str, str]
) -> str:
    template = PROMPT_TEMPLATE.read_text()
    journal_context = {
        "_run_context": {"resource_type": resource_type, "batch": batch},
        "_files": extra_files,
    }
    return (
        template + "\n\n## Journal context\n\n" + json.dumps(journal_context, indent=2)
    )


def run(
    enumerated_path: str | Path,
    resource_type: str,
    extra_files: list[str],
    batch_size: int = 20,
    role: str = "orchestrator",
    db_path=None,
) -> None:
    enumerated = json.loads(Path(enumerated_path).read_text())
    extra_file_contents = {p: Path(p).read_text() for p in extra_files}
    conn = connect(db_path) if db_path else connect()
    roles = load_roles()

    total = len(enumerated["properties"])
    batch_num = 0
    while True:
        remaining = _remaining_properties(conn, enumerated, resource_type)
        if not remaining:
            print(f"done: {total}/{total} properties classified for {resource_type}")
            return

        batch_num += 1
        batch = remaining[:batch_size]
        print(
            f"batch {batch_num}: classifying {len(batch)} properties "
            f"({total - len(remaining)}/{total} already done)"
        )
        prompt = _render_batch_prompt(resource_type, batch, extra_file_contents)

        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS_PER_BATCH + 1):
            try:
                raw_result = _invoke_claude(role, roles, prompt)
                classifications = _extract_json(raw_result)
                if isinstance(classifications, dict):
                    classifications = [classifications]
                inserted = apply_schema_classifications(conn, classifications)
                print(f"  inserted {inserted} classifications")
                last_error = None
                break
            except (WorkflowError, subprocess.TimeoutExpired) as exc:
                last_error = exc
                print(f"  attempt {attempt}/{MAX_ATTEMPTS_PER_BATCH} failed: {exc}")
                if attempt < MAX_ATTEMPTS_PER_BATCH:
                    time.sleep(RETRY_BACKOFF_SECONDS)

        if last_error is not None:
            raise WorkflowError(
                f"batch {batch_num} failed after {MAX_ATTEMPTS_PER_BATCH} attempts: {last_error}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("enumerated_path", type=Path)
    parser.add_argument("resource_type", type=str)
    parser.add_argument(
        "--extra-file",
        dest="extra_files",
        action="append",
        default=[],
        help="repo-relative path to include as supplementary context (repeatable)",
    )
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--role", type=str, default="orchestrator")
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()

    run(
        args.enumerated_path,
        args.resource_type,
        args.extra_files,
        batch_size=args.batch_size,
        role=args.role,
        db_path=args.db,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
