"""Report structured-discovery completion for a resource type.

"Done" is defined concretely here: every property in the deterministically
enumerated property list (harness/tools/enumerate_schema_properties.py)
has a corresponding row in the `schema_coverage` journal table. This
script is that comparison -- see docs/patterns/schema-coverage-discovery.md.

Usage:
    python -m harness.tools.coverage_status \
        sources/azure/storage/storage-account-properties.enumerated.json \
        "Microsoft.Storage/storageAccounts"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness.journal.db import connect


def coverage_status(
    enumerated_path: str | Path, resource_type: str, db_path=None
) -> dict:
    enumerated = json.loads(Path(enumerated_path).read_text())
    all_paths = {p["property_path"] for p in enumerated["properties"]}

    conn = connect(db_path) if db_path else connect()
    covered_rows = conn.execute(
        "SELECT property_path, relevant FROM schema_coverage WHERE resource_type = ?",
        (resource_type,),
    ).fetchall()
    covered_paths = {r["property_path"] for r in covered_rows}
    relevant_count = sum(1 for r in covered_rows if r["relevant"])

    remaining = sorted(all_paths - covered_paths)
    # Rows in schema_coverage with no match in the current enumeration --
    # expected after the source schema changes (a newer API version drops
    # or renames a property); not an error, just worth surfacing.
    stale = sorted(covered_paths - all_paths)

    return {
        "resource_type": resource_type,
        "total_properties": len(all_paths),
        "covered": len(covered_paths & all_paths),
        "relevant": relevant_count,
        "remaining": remaining,
        "stale": stale,
        "complete": not remaining,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("enumerated_path", type=Path)
    parser.add_argument("resource_type", type=str)
    parser.add_argument("--db", type=Path, default=None)
    args = parser.parse_args()

    status = coverage_status(args.enumerated_path, args.resource_type, args.db)
    print(f"resource_type: {status['resource_type']}")
    print(f"covered: {status['covered']}/{status['total_properties']}")
    print(f"  of which relevant (became hypotheses): {status['relevant']}")
    print(f"complete: {status['complete']}")
    if status["remaining"]:
        print(f"remaining ({len(status['remaining'])}):")
        for path in status["remaining"]:
            print(f"  - {path}")
    if status["stale"]:
        print(
            f"stale (in schema_coverage but not the current enumeration, {len(status['stale'])}):"
        )
        for path in status["stale"]:
            print(f"  - {path}")
    return 0 if status["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
