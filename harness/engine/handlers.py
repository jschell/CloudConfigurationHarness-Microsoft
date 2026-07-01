"""State handlers for the storage-atomic-tier workflow.

Each handler is referenced from a workflow YAML's `handler:` field and
receives (conn, state, context, raw_result) for LLM states or
(conn, state, context) for adapter/gate states. Handlers are the only
place that parses model JSON output and turns it into journal rows and
rule/fixture files on disk -- runner.py itself stays state-shape-agnostic.

Expected model output shapes (documented here since they are the schema
each prompt template must produce):

    schema_extract  -> JSON array of hypothesis objects matching the
                        `hypotheses` table columns (minus id/created_at).
    rule_compile    -> {"hypothesis_id", "check_id", "rule_path", "rego_content"}
    fixture_generate-> {"check_id", "fixture_dir", "vulnerable_bicep",
                         "safe_bicep", "ground_truth_method", "ground_truth_ref"}
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from harness.adapters import bicep_validate, rego_validate

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_RETRIES = 3


def _extract_json(raw_result: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Model output should be pure JSON; tolerate a fenced code block and/or
    leading prose by locating the outermost {...} or [...] span."""
    text = raw_result.strip()
    if "```" in text:
        fenced = text.split("```")[1]
        if fenced.startswith("json"):
            fenced = fenced[len("json") :]
        text = fenced.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        end = text.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"could not extract JSON from model output: {raw_result!r}")


def _extract_json_object(raw_result: str) -> dict[str, Any]:
    """Like `_extract_json`, but for handlers whose prompt template always
    asks for a single JSON object (rule_compile, fixture_generate) rather
    than an array."""
    parsed = _extract_json(raw_result)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"expected a JSON object, got {type(parsed).__name__}: {parsed!r}"
        )
    return parsed


def schema_extract(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    context: dict[str, Any],
    raw_result: str,
) -> bool:
    hypotheses = _extract_json(raw_result)
    if isinstance(hypotheses, dict):
        hypotheses = [hypotheses]
    for hyp in hypotheses:
        conn.execute(
            """INSERT INTO hypotheses
               (resource_type, property_path, risky_value, safe_value, rationale,
                source_doc, existing_policy_ref, proposed_by_model, tier, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed')""",
            (
                hyp["resource_type"],
                hyp["property_path"],
                hyp.get("risky_value"),
                hyp.get("safe_value"),
                hyp["rationale"],
                hyp["source_doc"],
                hyp.get("existing_policy_ref"),
                hyp["proposed_by_model"],
                hyp["tier"],
            ),
        )
    conn.commit()
    return True


def rule_compile(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    context: dict[str, Any],
    raw_result: str,
) -> bool:
    parsed = _extract_json_object(raw_result)
    check_id = parsed["check_id"]
    rule_path = parsed["rule_path"]

    full_path = REPO_ROOT / rule_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(parsed["rego_content"])

    existing = conn.execute(
        "SELECT id FROM rules WHERE check_id = ?", (check_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE rules SET rule_path = ?, status = 'draft' WHERE check_id = ?",
            (rule_path, check_id),
        )
    else:
        conn.execute(
            "INSERT INTO rules (hypothesis_id, check_id, rule_path, status) "
            "VALUES (?, ?, ?, 'draft')",
            (parsed["hypothesis_id"], check_id, rule_path),
        )
    # Append-only, unlike the `rules` row above -- see schema.sql. Lets
    # compare_runs.py recover exactly what *this* run produced even if a
    # later run targeting the same check_id overwrites `rules`/the file.
    conn.execute(
        "INSERT INTO rule_history (workflow_run_id, check_id, rule_path, rego_content) "
        "VALUES (?, ?, ?, ?)",
        (context.get("_workflow_run_id"), check_id, rule_path, parsed["rego_content"]),
    )
    conn.commit()
    context["check_id"] = check_id
    return True


def fixture_generate(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    context: dict[str, Any],
    raw_result: str,
) -> bool:
    parsed = _extract_json_object(raw_result)
    check_id = parsed["check_id"]
    fixture_dir = REPO_ROOT / parsed["fixture_dir"]
    fixture_dir.mkdir(parents=True, exist_ok=True)

    (fixture_dir / "vulnerable.bicep").write_text(parsed["vulnerable_bicep"])
    (fixture_dir / "safe.bicep").write_text(parsed["safe_bicep"])

    existing = conn.execute(
        "SELECT id FROM fixtures WHERE check_id = ?", (check_id,)
    ).fetchone()
    if existing:
        fixture_id = existing["id"]
        conn.execute(
            "UPDATE fixtures SET fixture_path = ?, ground_truth_method = ?, ground_truth_ref = ? "
            "WHERE id = ?",
            (
                parsed["fixture_dir"],
                parsed["ground_truth_method"],
                parsed.get("ground_truth_ref"),
                fixture_id,
            ),
        )
    else:
        cur = conn.execute(
            "INSERT INTO fixtures (check_id, fixture_path, ground_truth_method, ground_truth_ref) "
            "VALUES (?, ?, ?, ?)",
            (
                check_id,
                parsed["fixture_dir"],
                parsed["ground_truth_method"],
                parsed.get("ground_truth_ref"),
            ),
        )
        fixture_id = cur.lastrowid
    # Append-only, unlike the `fixtures` row above -- see schema.sql and
    # the matching note in rule_compile().
    conn.execute(
        "INSERT INTO fixture_history "
        "(workflow_run_id, check_id, fixture_path, vulnerable_bicep, safe_bicep, "
        "ground_truth_method, ground_truth_ref) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            context.get("_workflow_run_id"),
            check_id,
            parsed["fixture_dir"],
            parsed["vulnerable_bicep"],
            parsed["safe_bicep"],
            parsed["ground_truth_method"],
            parsed.get("ground_truth_ref"),
        ),
    )
    conn.commit()
    context["check_id"] = check_id
    context["fixture_id"] = fixture_id
    return True


def fixture_validate(
    conn: sqlite3.Connection, state: dict[str, Any], context: dict[str, Any]
) -> bool:
    """Deterministic adapter state: no LLM. Compiles both fixtures to JSON
    and runs the Rego adapter against each, writing two `runs` rows."""
    check_id = context["check_id"]
    fixture_row = conn.execute(
        "SELECT * FROM fixtures WHERE check_id = ?", (check_id,)
    ).fetchone()
    rule_row = conn.execute(
        "SELECT * FROM rules WHERE check_id = ?", (check_id,)
    ).fetchone()

    fixture_dir = REPO_ROOT / fixture_row["fixture_path"]
    policy_dir = (REPO_ROOT / rule_row["rule_path"]).parent

    for label, expected_verdict in (("vulnerable", "fail"), ("safe", "pass")):
        bicep_path = fixture_dir / f"{label}.bicep"
        json_path = fixture_dir / f"{label}.json"
        try:
            bicep_validate.bicep_to_json(bicep_path, json_path)
        except RuntimeError as exc:
            result = {
                "adapter": "bicep_validate",
                "actual_verdict": "error",
                "expected_verdict": expected_verdict,
                "passed": False,
                "raw_output": str(exc),
            }
        else:
            result = rego_validate.validate(
                json_path, policy_dir, expected_verdict, check_id
            )

        conn.execute(
            """INSERT INTO runs
               (check_id, fixture_id, adapter, expected_verdict, actual_verdict, passed, raw_output)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                check_id,
                fixture_row["id"],
                result["adapter"],
                result["expected_verdict"],
                result["actual_verdict"],
                1 if result["passed"] else 0,
                f"[{label}] " + (result["raw_output"] or ""),
            ),
        )
    conn.commit()
    return True


def gate(
    conn: sqlite3.Connection, state: dict[str, Any], context: dict[str, Any]
) -> bool:
    """Pure logic, no LLM/adapter call: evaluate the latest two `runs` rows
    for the current check_id.

    Returns True (terminal -- next_on_success) when the rule reaches either
    'validated' or 'rejected' (retries exhausted). Returns False
    (next_on_failure -> loop back to rule_compile) only while retries remain.
    """
    check_id = context["check_id"]
    runs = conn.execute(
        "SELECT * FROM runs WHERE check_id = ? ORDER BY id DESC LIMIT 2", (check_id,)
    ).fetchall()

    all_passed = len(runs) == 2 and all(r["passed"] for r in runs)

    if all_passed:
        conn.execute(
            "UPDATE rules SET status = 'validated' WHERE check_id = ?", (check_id,)
        )
        conn.commit()
        return True

    retries = context.setdefault("retries", {})
    retries[check_id] = retries.get(check_id, 0) + 1
    failure_reasons = [
        f"{r['adapter']}: expected={r['expected_verdict']} actual={r['actual_verdict']}"
        for r in runs
    ]
    context["last_failure_reason"] = failure_reasons

    if retries[check_id] >= MAX_RETRIES:
        conn.execute(
            "UPDATE rules SET status = 'rejected' WHERE check_id = ?", (check_id,)
        )
        conn.commit()
        print(
            f"[gate] check_id={check_id} rejected after {retries[check_id]} attempts; "
            f"human review flagged. Reasons: {failure_reasons}"
        )
        return True

    return False
