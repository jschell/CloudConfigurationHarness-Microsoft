"""State handlers for atomic-tier (Tier 1) FSM workflows.

Each handler is referenced from a workflow YAML's `handler:` field and
receives (conn, state, context, raw_result) for LLM states or
(conn, state, context) for adapter/gate states. Handlers are the only
place that parses model JSON output and turns it into journal rows and
rule/fixture files on disk -- runner.py itself stays state-shape-agnostic.

Generic across resource types (see docs/onboarding-new-resource-type.md):
rule_compile/fixture_generate read check_id_prefix/rules_dir/fixtures_dir
from context["_resource_config"] (set by Runner.start() from the
workflow YAML's top-level `resource_config`), not hardcoded constants.
A new resource type's own workflow YAML supplies its own resource_config
-- nothing in this file should need to change to onboard one.

Expected model output shapes (documented here since they are the schema
each prompt template must produce):

    schema_extract  -> JSON array of classification objects (see
                        schema_coverage below), one per property in the
                        enumerated property list the prompt was given --
                        NOT just the security-relevant ones.
    rule_compile    -> {"hypothesis_id", "rego_content"}
    fixture_generate-> {"variants": [{"label", "expected_verdict", "bicep"}, ...],
                         "ground_truth_method", "ground_truth_ref"}
                        Tier 1 hypotheses produce exactly two variants
                        ("vulnerable"/fail, "safe"/pass); Tier 2 hypotheses
                        (multiple property_conditions) produce one variant
                        per combination worth covering.

check_id/rule_path/fixture_dir are deliberately NOT part of either
output schema and are never read from the model even if present --
see docs/patterns/deterministic-check-id-assignment.md. The model has
no reliable way to know which check_id numbers are already taken (each
call is a stateless CLI invocation with no memory of prior calls), and
letting it invent one caused a real check_id collision that silently
overwrote three already-validated rules before being caught (2026-07-02).
`_check_id_for_hypothesis` assigns it deterministically instead.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from harness.adapters import bicep_validate, rego_validate

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_RETRIES = 3


def _resource_config(context: dict[str, Any]) -> dict[str, str]:
    config = context.get("_resource_config")
    if not config:
        raise KeyError(
            "context is missing _resource_config -- Runner.start() sets this "
            "from the workflow YAML's top-level resource_config; see "
            "docs/onboarding-new-resource-type.md"
        )
    return config


def _balanced_spans(text: str) -> list[tuple[int, int]]:
    """Every top-level (start, end) span of a balanced {...} or [...] in
    text -- "top-level" meaning outermost only, tracking combined depth
    across both bracket types so an object nested inside an array isn't
    also recorded as its own span -- ignoring brackets/braces inside
    string literals (Rego rule bodies routinely contain `{`/`}`, so naive
    per-character counting without string-awareness would miscount)."""
    spans = []
    depth = 0
    start = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in "{[":
            if depth == 0:
                start = i
            depth += 1
        elif ch in "}]":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append((start, i))
    return spans


def _extract_json(raw_result: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Model output should be pure JSON; tolerate a fenced code block
    and/or leading prose. If the model second-guesses itself and emits
    more than one top-level JSON blob (draft, then "wait, let me
    reconsider", then a revised one), prefer the LAST one that parses --
    it supersedes what came before. Confirmed live: a rule_compile
    response containing two {...} blocks (a draft and a corrected
    version) broke the old naive first-'{'-to-last-'}' span, which
    spanned both blobs plus the prose between them."""
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

    spans = _balanced_spans(text)
    for start, end in sorted(spans, key=lambda pair: pair[0], reverse=True):
        try:
            return json.loads(text[start : end + 1])
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


def apply_schema_classifications(
    conn: sqlite3.Connection, classifications: list[dict[str, Any]]
) -> int:
    """Insert a batch of property classifications into
    `schema_coverage`/`hypotheses`. Shared by the `schema_extract` FSM
    handler (one call, whatever the model proposes) and
    `harness.tools.run_schema_coverage` (many small batched calls) -- see
    docs/patterns/schema-coverage-discovery.md. `schema_coverage` is the
    completeness ledger and the dedup guard: a (resource_type,
    property_path) already present there is skipped regardless of what
    the model says about it this call, so a model re-proposing something
    already decided (or hallucinating a duplicate) can't corrupt the
    ledger or double-insert a hypothesis. Returns the number of rows
    actually inserted (i.e. excluding skipped duplicates).
    """
    inserted = 0
    for item in classifications:
        resource_type = item["resource_type"]
        property_path = item["property_path"]

        already_covered = conn.execute(
            "SELECT 1 FROM schema_coverage WHERE resource_type = ? AND property_path = ?",
            (resource_type, property_path),
        ).fetchone()
        if already_covered:
            continue

        relevant = bool(item["relevant"])
        hypothesis_id = None
        if relevant:
            cur = conn.execute(
                """INSERT INTO hypotheses
                   (resource_type, property_path, risky_value, safe_value, rationale,
                    source_doc, existing_policy_ref, proposed_by_model, tier, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed')""",
                (
                    resource_type,
                    property_path,
                    item.get("risky_value"),
                    item.get("safe_value"),
                    item["rationale"],
                    item["source_doc"],
                    item.get("existing_policy_ref"),
                    item["proposed_by_model"],
                    item["tier"],
                ),
            )
            hypothesis_id = cur.lastrowid

        conn.execute(
            "INSERT INTO schema_coverage "
            "(resource_type, property_path, relevant, rationale, hypothesis_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                resource_type,
                property_path,
                1 if relevant else 0,
                item["rationale"],
                hypothesis_id,
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def schema_extract(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    context: dict[str, Any],
    raw_result: str,
) -> bool:
    classifications = _extract_json(raw_result)
    if isinstance(classifications, dict):
        classifications = [classifications]
    apply_schema_classifications(conn, classifications)
    return True


def _check_id_for_hypothesis(
    conn: sqlite3.Connection, hypothesis_id: int, check_id_prefix: str
) -> tuple[str, bool]:
    """Deterministically assign a check_id -- the model is never asked to
    invent one (see the module docstring). Returns (check_id, is_retry):
    is_retry=True means `rules` already has a row for this hypothesis
    (a gate-triggered rule_compile retry), so its existing check_id is
    reused rather than minted fresh. Never reuses a number that appears
    anywhere in `rules` OR `rule_history` FOR THIS PREFIX, so a
    superseded/overwritten check_id's number is never handed out again
    either -- scoped to check_id_prefix so two resource types' numbering
    (e.g. AZ-STOR-* and a future AZ-VM-*) never interfere with each other.
    """
    existing = conn.execute(
        "SELECT check_id FROM rules WHERE hypothesis_id = ?", (hypothesis_id,)
    ).fetchone()
    if existing:
        return existing["check_id"], True

    like_pattern = f"{check_id_prefix}-%"
    numbers = []
    for table in ("rules", "rule_history"):
        for row in conn.execute(
            f"SELECT DISTINCT check_id FROM {table} WHERE check_id LIKE ?",
            (like_pattern,),
        ).fetchall():
            match = re.search(r"(\d+)$", row["check_id"])
            if match:
                numbers.append(int(match.group(1)))
    next_number = max(numbers, default=0) + 1
    return f"{check_id_prefix}-{next_number:03d}", False


def rule_compile(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    context: dict[str, Any],
    raw_result: str,
) -> bool:
    parsed = _extract_json_object(raw_result)
    hypothesis_id = parsed["hypothesis_id"]
    config = _resource_config(context)
    check_id, is_retry = _check_id_for_hypothesis(
        conn, hypothesis_id, config["check_id_prefix"]
    )
    rule_path = f"{config['rules_dir']}/{check_id}.rego"
    namespace = "checks." + check_id.lower().replace("-", "_")
    # The model can't know the correct package name in advance either
    # (it doesn't know check_id), so it writes a placeholder and the
    # handler substitutes the real one here -- same reasoning as check_id
    # itself being handler-assigned, not model-assigned.
    rego_content = re.sub(
        r"^package\s+\S+",
        f"package {namespace}",
        parsed["rego_content"],
        count=1,
        flags=re.MULTILINE,
    )

    full_path = REPO_ROOT / rule_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(rego_content)

    if is_retry:
        conn.execute(
            "UPDATE rules SET rule_path = ?, status = 'draft' WHERE check_id = ?",
            (rule_path, check_id),
        )
    else:
        conn.execute(
            "INSERT INTO rules (hypothesis_id, check_id, rule_path, status) "
            "VALUES (?, ?, ?, 'draft')",
            (hypothesis_id, check_id, rule_path),
        )
    # Append-only, unlike the `rules` row above -- see schema.sql. Lets
    # compare_runs.py recover exactly what *this* run produced even if a
    # later run targeting the same check_id overwrites `rules`/the file.
    conn.execute(
        "INSERT INTO rule_history (workflow_run_id, check_id, rule_path, rego_content) "
        "VALUES (?, ?, ?, ?)",
        (context.get("_workflow_run_id"), check_id, rule_path, rego_content),
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
    # Authoritative: set by rule_compile earlier in this same run, not
    # echoed back by the model (same reasoning as rule_compile's check_id
    # -- see the module docstring and _check_id_for_hypothesis).
    check_id = context["check_id"]
    config = _resource_config(context)
    fixture_path = f"{config['fixtures_dir']}/{check_id}"
    fixture_dir = REPO_ROOT / fixture_path
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # variants: [{"label", "expected_verdict", "bicep"}, ...]. Tier 1
    # hypotheses produce the same two variants ("vulnerable"/fail,
    # "safe"/pass) that used to be hardcoded here; Tier 2 hypotheses can
    # produce more, one per property_conditions combination.
    variants = parsed["variants"]
    for variant in variants:
        (fixture_dir / f"{variant['label']}.bicep").write_text(variant["bicep"])
    variants_json = json.dumps(
        [
            {"label": v["label"], "expected_verdict": v["expected_verdict"]}
            for v in variants
        ]
    )
    bicep_files_json = json.dumps({v["label"]: v["bicep"] for v in variants})

    existing = conn.execute(
        "SELECT id FROM fixtures WHERE check_id = ?", (check_id,)
    ).fetchone()
    if existing:
        fixture_id = existing["id"]
        conn.execute(
            "UPDATE fixtures SET fixture_path = ?, variants_json = ?, "
            "ground_truth_method = ?, ground_truth_ref = ? WHERE id = ?",
            (
                fixture_path,
                variants_json,
                parsed["ground_truth_method"],
                parsed.get("ground_truth_ref"),
                fixture_id,
            ),
        )
    else:
        cur = conn.execute(
            "INSERT INTO fixtures (check_id, fixture_path, variants_json, "
            "ground_truth_method, ground_truth_ref) VALUES (?, ?, ?, ?, ?)",
            (
                check_id,
                fixture_path,
                variants_json,
                parsed["ground_truth_method"],
                parsed.get("ground_truth_ref"),
            ),
        )
        fixture_id = cur.lastrowid
    # Append-only, unlike the `fixtures` row above -- see schema.sql and
    # the matching note in rule_compile(). vulnerable_bicep/safe_bicep stay
    # populated (first fail/pass variant) for backward compat with rows
    # written before variants existed; variants_json/bicep_files_json are
    # authoritative going forward.
    first_fail = next(
        (v["bicep"] for v in variants if v["expected_verdict"] == "fail"), ""
    )
    first_pass = next(
        (v["bicep"] for v in variants if v["expected_verdict"] == "pass"), ""
    )
    conn.execute(
        "INSERT INTO fixture_history "
        "(workflow_run_id, check_id, fixture_path, vulnerable_bicep, safe_bicep, "
        "variants_json, bicep_files_json, ground_truth_method, ground_truth_ref) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            context.get("_workflow_run_id"),
            check_id,
            fixture_path,
            first_fail,
            first_pass,
            variants_json,
            bicep_files_json,
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
    """Deterministic adapter state: no LLM. Compiles every fixture variant
    to JSON and runs the Rego adapter against each, writing one `runs` row
    per variant (two for Tier 1, more for Tier 2 combinations)."""
    check_id = context["check_id"]
    fixture_row = conn.execute(
        "SELECT * FROM fixtures WHERE check_id = ?", (check_id,)
    ).fetchone()
    rule_row = conn.execute(
        "SELECT * FROM rules WHERE check_id = ?", (check_id,)
    ).fetchone()

    fixture_dir = REPO_ROOT / fixture_row["fixture_path"]
    policy_dir = (REPO_ROOT / rule_row["rule_path"]).parent

    # variants_json is NULL for fixtures written before Tier 2 existed;
    # fall back to the old hardcoded pair so historical rows keep working.
    if fixture_row["variants_json"]:
        variants = json.loads(fixture_row["variants_json"])
    else:
        variants = [
            {"label": "vulnerable", "expected_verdict": "fail"},
            {"label": "safe", "expected_verdict": "pass"},
        ]

    for variant in variants:
        label = variant["label"]
        expected_verdict = variant["expected_verdict"]
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
    """Pure logic, no LLM/adapter call: evaluate the latest batch of `runs`
    rows for the current check_id (one row per fixture variant -- two for
    Tier 1, more for Tier 2 combinations).

    Returns True (terminal -- next_on_success) when the rule reaches either
    'validated' or 'rejected' (retries exhausted). Returns False
    (next_on_failure -> loop back to rule_compile) only while retries remain.
    """
    check_id = context["check_id"]
    fixture_row = conn.execute(
        "SELECT variants_json FROM fixtures WHERE check_id = ?", (check_id,)
    ).fetchone()
    expected_run_count = (
        len(json.loads(fixture_row["variants_json"]))
        if fixture_row["variants_json"]
        else 2
    )
    runs = conn.execute(
        "SELECT * FROM runs WHERE check_id = ? ORDER BY id DESC LIMIT ?",
        (check_id, expected_run_count),
    ).fetchall()

    all_passed = len(runs) == expected_run_count and all(r["passed"] for r in runs)

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
