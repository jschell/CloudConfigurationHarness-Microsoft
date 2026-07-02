# Feature: Tier 2 (pattern/combination) checks

## Goal

Let the harness discover, compile, and validate hypotheses where a
*combination* of properties on one resource is risky even though no
single property is risky alone (e.g. `allowSharedKeyAccess=true`
combined with `networkAcls.defaultAction=Allow` is worse than either
alone) -- while leaving every existing Tier 1 (atomic) check, rule, and
fixture completely unaffected.

## Architecture

Reuse the existing FSM shape (`discover -> rule_compile ->
fixture_generate -> fixture_validate -> gate`) and the existing
`hypotheses`/`rules`/`fixtures`/`runs` tables, rather than building a
parallel system. Three things are genuinely new:

1. **`hypotheses` needs to describe more than one property per row.**
   Tier 1 hypotheses use the existing flat `property_path`/
   `risky_value`/`safe_value` columns, unchanged. Tier 2 hypotheses
   populate a new nullable `property_conditions` JSON column instead
   (a list of `{property_path, risky_value, safe_value}`), leaving
   `property_path` as a human-readable joined summary (the column is
   `NOT NULL`; a schema migration to make it nullable is out of scope --
   YAGNI, this is not the state the column is `NOT NULL` for).
2. **Discovery can't be exhaustive the way Tier 1's `schema_coverage`
   sweep is.** Even just *pairs* of Storage's 72 writable properties is
   ~2,500 combinations -- too many to classify one by one. Tier 2
   discovery (`pattern_extract`) is a different kind of LLM task:
   propose a handful of plausible combinations reasoning from known
   attack patterns, not exhaustively enumerate.
3. **Fixture validation needs more than two variants.** Tier 1 proves a
   rule with `vulnerable`/`safe` fixtures. Tier 2 needs `vulnerable`
   (all conditions risky), `safe` (all conditions safe), and one "mixed"
   fixture per condition (only that one condition risky) to prove the
   rule is actually testing the *combination* and not silently
   degenerating into a single-property check. `fixture_generate`/
   `fixture_validate`/`gate` currently hardcode exactly two variants in
   three separate places -- this needs generalizing to an N-variant list
   first, as a no-behavior-change refactor for Tier 1, before Tier 2 can
   use more than two.

Everything else -- `rule_compile`'s check_id/package assignment,
`_resource_config`, the dedup/history tables -- already works
per-hypothesis regardless of tier and needs no change.

## Tech Stack

Same as the rest of the harness: Python 3.11, SQLite, YAML workflow
definitions, `az bicep build` + `conftest` as the deterministic verifier.
**No automated test suite exists in this repo** (`pyproject.toml`
declares `pytest` as a dev dependency but there are no test files) --
every task in this plan is a real end-to-end run against the live
journal and real `az`/`conftest`, matching how every prior task in this
project was actually verified (see `docs/status/*.md`). Where the
"writing-plans" skill's step template says "write test / verify failure
/ implement / verify pass," read that as "write the verification script
/ run it to confirm the gap exists / implement / run it again to confirm
it's fixed" -- adapted to this project's demonstrated tooling loop
rather than inventing a pytest suite that doesn't match how this
codebase is actually verified.

**Environment reminders** (see `docs/operating-tiers.md`): export
`UV_LINK_MODE=copy`; prepend `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin`
to `PATH` if `az` reports MISS; **never run `rule_compile`/
`fixture_generate` against a scratch `--db` without first seeding it
with dummy rows for every real check_id already in use** (file writes
are `REPO_ROOT`-relative regardless of `--db` -- this bit a previous
session for real).

## Tasks

### Task 1: Schema migration for multi-property hypotheses and N-variant fixtures

**Files:** `harness/journal/schema.sql`, `harness/journal/db.py`

#### Steps:

1. Verify the gap first -- confirm `hypotheses` has no way to store more
   than one property today:
   ```bash
   uv run --frozen python -c "
   import sys; sys.path.insert(0, '.')
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   cols = {r['name'] for r in conn.execute('PRAGMA table_info(hypotheses)')}
   assert 'property_conditions' not in cols, 'already exists -- skip this task'
   print('confirmed: property_conditions does not exist yet')
   "
   ```
   Expect: `confirmed: property_conditions does not exist yet`.

2. Update `harness/journal/schema.sql` so a **fresh** database already
   has the new columns (existing databases are handled by step 3's
   migration). In the `hypotheses` table definition (currently lines
   4-17), add one column and a clarifying comment:
   ```sql
   CREATE TABLE IF NOT EXISTS hypotheses (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     resource_type TEXT NOT NULL,           -- e.g. Microsoft.Storage/storageAccounts
     property_path TEXT NOT NULL,           -- e.g. properties.networkAcls.defaultAction
                                             -- for tier>=2, a human-readable joined summary
                                             -- of the properties in property_conditions
                                             -- (this column stays NOT NULL; the real,
                                             -- structured data for tier>=2 lives in
                                             -- property_conditions instead)
     risky_value TEXT,
     safe_value TEXT,
     property_conditions TEXT,              -- JSON list of {property_path, risky_value,
                                             -- safe_value}, tier>=2 only. NULL for tier 1,
                                             -- which keeps using the three columns above.
     rationale TEXT NOT NULL,
     source_doc TEXT NOT NULL,              -- URL or repo path + commit SHA
     existing_policy_ref TEXT,              -- Azure built-in Policy name, nullable
     proposed_by_model TEXT NOT NULL,       -- e.g. claude-opus-4-8, glm-5.2
     tier INTEGER NOT NULL,                 -- 1=atomic, 2=pattern, 3=chained
     status TEXT NOT NULL DEFAULT 'proposed', -- proposed | promoted | rejected
     created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );
   ```

3. In the `fixtures` table definition (currently lines 51-58), add
   `variants_json`:
   ```sql
   CREATE TABLE IF NOT EXISTS fixtures (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     check_id TEXT NOT NULL REFERENCES rules(check_id),
     fixture_path TEXT NOT NULL,            -- dir under fixtures/
     variants_json TEXT,                    -- JSON list of {label, expected_verdict}.
                                             -- NULL means the Tier 1 default:
                                             -- [{"label":"vulnerable","expected_verdict":"fail"},
                                             --  {"label":"safe","expected_verdict":"pass"}]
     ground_truth_method TEXT NOT NULL,     -- e.g. azure-policy-builtin, manual-expert, iam-simulator
     ground_truth_ref TEXT,                 -- policy definition ID or reviewer name
     created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );
   ```

4. In `fixture_history` (currently lines 101-111), add
   `variants_json`/`bicep_files_json`, keeping the old columns for
   backward compatibility with rows already written:
   ```sql
   CREATE TABLE IF NOT EXISTS fixture_history (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     workflow_run_id INTEGER REFERENCES workflow_runs(id),
     check_id TEXT NOT NULL,
     fixture_path TEXT NOT NULL,
     vulnerable_bicep TEXT NOT NULL,        -- kept for backward compat with existing rows;
                                             -- new writes populate this with the first
                                             -- "fail"-expected variant's content
     safe_bicep TEXT NOT NULL,              -- same, first "pass"-expected variant
     variants_json TEXT,                    -- authoritative for new writes: JSON list of
                                             -- {label, expected_verdict}
     bicep_files_json TEXT,                 -- authoritative for new writes: JSON dict of
                                             -- {label: bicep_content}
     ground_truth_method TEXT,
     ground_truth_ref TEXT,
     created_at TEXT NOT NULL DEFAULT (datetime('now'))
   );
   ```

5. `CREATE TABLE IF NOT EXISTS` does not add columns to a table that
   already exists (the real journal already has all four tables above).
   Add a small idempotent column-migration helper to
   `harness/journal/db.py`, replacing the current `migrate()` (lines
   28-31):
   ```python
   def migrate(conn: sqlite3.Connection) -> None:
       """Apply schema.sql against an existing connection. Idempotent."""
       conn.executescript(SCHEMA_PATH.read_text())
       _add_column_if_missing(conn, "hypotheses", "property_conditions", "TEXT")
       _add_column_if_missing(conn, "fixtures", "variants_json", "TEXT")
       _add_column_if_missing(conn, "fixture_history", "variants_json", "TEXT")
       _add_column_if_missing(conn, "fixture_history", "bicep_files_json", "TEXT")
       conn.commit()


   def _add_column_if_missing(
       conn: sqlite3.Connection, table: str, column: str, sql_type: str
   ) -> None:
       existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
       if column not in existing:
           conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
   ```

6. Verify against the real journal (safe -- purely additive, no existing
   data touched):
   ```bash
   uv run --frozen python -c "
   import sys; sys.path.insert(0, '.')
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   for table, col in [('hypotheses','property_conditions'), ('fixtures','variants_json'),
                       ('fixture_history','variants_json'), ('fixture_history','bicep_files_json')]:
       cols = {r['name'] for r in conn.execute(f'PRAGMA table_info({table})')}
       assert col in cols, f'{table}.{col} missing'
   # confirm nothing about the existing 41 checks changed
   print(conn.execute('SELECT COUNT(*) as n FROM rules').fetchone()['n'], 'rules (expect 41)')
   "
   ```
   Expect: no assertion errors, `41 rules (expect 41)`.

7. Run `ruff format`, `ruff check`, `pyright` on the touched file:
   ```bash
   uv run --frozen ruff format harness/journal/db.py
   uv run --frozen ruff check harness/journal/db.py
   uv run --frozen pyright harness/journal/db.py
   ```
   Expect: all clean.

8. Commit: `"Add schema columns for Tier 2 multi-property hypotheses and N-variant fixtures"`

### Task 2: Generalize fixtures to an N-variant list (no behavior change for Tier 1)

**File:** `harness/engine/handlers.py`

This is the highest-risk task in the plan -- it changes the *output
contract* `fixture_generate.md` asks the model for for every future run,
including Tier 1. Verify old data is untouched and new Tier 1 runs still
work identically before moving on.

#### Steps:

1. Confirm the current hardcoding (three separate places assume exactly
   two variants):
   ```bash
   grep -n '"vulnerable", "fail"\|"safe", "pass"\|len(runs) == 2\|LIMIT 2' harness/engine/handlers.py
   ```
   Expect three hits: inside `fixture_validate`, inside `gate`, and the
   `LIMIT 2` in `gate`'s query.

2. In `harness/engine/handlers.py`, replace `fixture_generate` (current
   lines 306-371) to accept a `variants` list from the model instead of
   fixed `vulnerable_bicep`/`safe_bicep` keys:
   ```python
   def fixture_generate(
       conn: sqlite3.Connection,
       state: dict[str, Any],
       context: dict[str, Any],
       raw_result: str,
   ) -> bool:
       parsed = _extract_json_object(raw_result)
       check_id = context["check_id"]
       config = _resource_config(context)
       fixture_path = f"{config['fixtures_dir']}/{check_id}"
       fixture_dir = REPO_ROOT / fixture_path
       fixture_dir.mkdir(parents=True, exist_ok=True)

       variants = parsed["variants"]  # [{"label", "expected_verdict", "bicep"}, ...]
       for variant in variants:
           (fixture_dir / f"{variant['label']}.bicep").write_text(variant["bicep"])
       variants_json = json.dumps(
           [{"label": v["label"], "expected_verdict": v["expected_verdict"]} for v in variants]
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

       # vulnerable_bicep/safe_bicep stay NOT NULL for backward compat with
       # existing rows -- populate from the first fail/pass variant so the
       # constraint holds; bicep_files_json/variants_json are authoritative.
       first_fail = next((v["bicep"] for v in variants if v["expected_verdict"] == "fail"), "")
       first_pass = next((v["bicep"] for v in variants if v["expected_verdict"] == "pass"), "")
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
   ```

3. Replace `fixture_validate` (current lines 374-423) to read variants
   from the fixture row, defaulting to the Tier 1 shape when
   `variants_json` is NULL (old rows created before this task):
   ```python
   def fixture_validate(
       conn: sqlite3.Connection, state: dict[str, Any], context: dict[str, Any]
   ) -> bool:
       """Deterministic adapter state: no LLM. Compiles each fixture variant
       to JSON and runs the Rego adapter against it, writing one `runs` row
       per variant."""
       check_id = context["check_id"]
       fixture_row = conn.execute(
           "SELECT * FROM fixtures WHERE check_id = ?", (check_id,)
       ).fetchone()
       rule_row = conn.execute(
           "SELECT * FROM rules WHERE check_id = ?", (check_id,)
       ).fetchone()

       fixture_dir = REPO_ROOT / fixture_row["fixture_path"]
       policy_dir = (REPO_ROOT / rule_row["rule_path"]).parent

       variants = (
           json.loads(fixture_row["variants_json"])
           if fixture_row["variants_json"]
           else [
               {"label": "vulnerable", "expected_verdict": "fail"},
               {"label": "safe", "expected_verdict": "pass"},
           ]
       )

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
               result = rego_validate.validate(json_path, policy_dir, expected_verdict, check_id)

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
   ```

4. In `gate` (current lines 426-468), replace the hardcoded `LIMIT 2`/
   `== 2` with the actual variant count for this check_id:
   ```python
   def gate(
       conn: sqlite3.Connection, state: dict[str, Any], context: dict[str, Any]
   ) -> bool:
       """Pure logic, no LLM/adapter call: evaluate the latest N `runs` rows
       for the current check_id, where N is this check's fixture variant
       count (2 for Tier 1, more for Tier 2 -- see fixtures.variants_json).

       Returns True (terminal -- next_on_success) when the rule reaches either
       'validated' or 'rejected' (retries exhausted). Returns False
       (next_on_failure -> loop back to rule_compile) only while retries remain.
       """
       check_id = context["check_id"]
       fixture_row = conn.execute(
           "SELECT variants_json FROM fixtures WHERE check_id = ?", (check_id,)
       ).fetchone()
       variant_count = (
           len(json.loads(fixture_row["variants_json"]))
           if fixture_row and fixture_row["variants_json"]
           else 2
       )

       runs = conn.execute(
           "SELECT * FROM runs WHERE check_id = ? ORDER BY id DESC LIMIT ?",
           (check_id, variant_count),
       ).fetchall()

       all_passed = len(runs) == variant_count and all(r["passed"] for r in runs)

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
   ```

5. Update `harness/workflows/prompts/fixture_generate.md`'s output
   contract from the fixed `vulnerable_bicep`/`safe_bicep` keys to a
   `variants` list. Replace its final "Reply with ONLY a JSON object"
   section with:
   ```
   Reply with ONLY a JSON object (no markdown fences, no prose). `variants`
   is a list -- exactly two entries (`vulnerable`, `safe`) for a
   single-property hypothesis; for a multi-property (combination)
   hypothesis, include one "all risky" variant, one "all safe" variant,
   and one "mixed" variant per condition where only that one condition is
   risky and the rest are safe (proving the rule fires on the full
   combination, not on any single property in isolation):

       {
         "variants": [
           {"label": "vulnerable", "expected_verdict": "fail", "bicep": "<full .bicep file contents>"},
           {"label": "safe", "expected_verdict": "pass", "bicep": "<full .bicep file contents>"}
         ],
         "ground_truth_method": "azure-policy-builtin | manual-expert | iam-simulator",
         "ground_truth_ref": "<policy definition ID or reviewer name, or null>"
       }
   ```

6. Format/lint/typecheck:
   ```bash
   uv run --frozen ruff format harness/engine/handlers.py
   uv run --frozen ruff check harness/engine/handlers.py
   uv run --frozen pyright harness/engine/handlers.py
   ```
   Expect: all clean.

7. **Verify no regression on existing data**: all 41 already-committed
   Storage rules must still validate against the unchanged
   `fixture_validate` default-variants fallback (their `fixtures` rows
   have `variants_json IS NULL`):
   ```bash
   uv run --frozen python -c "
   import sys; sys.path.insert(0, '.')
   from harness.journal.db import connect
   from harness.adapters import bicep_validate, rego_validate
   from pathlib import Path

   conn = connect('harness/journal/harness.db')
   policy_dir = Path('rules/azure/storage')
   all_ok = True
   rows = conn.execute('SELECT check_id FROM rules ORDER BY check_id').fetchall()
   print(f'checking {len(rows)} rules')
   for r in rows:
       check_id = r['check_id']
       fixture_dir = Path(f'fixtures/azure/storage/{check_id}')
       for label, expected in (('vulnerable', 'fail'), ('safe', 'pass')):
           json_path = fixture_dir / f'{label}.json'
           bicep_validate.bicep_to_json(fixture_dir / f'{label}.bicep', json_path)
           result = rego_validate.validate(json_path, policy_dir, expected, check_id)
           all_ok &= result['passed']
           if not result['passed']:
               print(check_id, label, '-> FAIL')
   print('ALL PASSED' if all_ok else 'SOME FAILED')
   "
   ```
   Expect: `checking 41 rules` then `ALL PASSED`.

8. **Verify a brand-new Tier 1 run still works end to end** with the new
   `variants`-list contract (targets any not-yet-compiled hypothesis, or
   seed one in a scratch db per `docs/operating-tiers.md`'s hazard
   warning if none remain):
   ```bash
   uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml \
     --start-state rule_compile --context '{"target_hypothesis_id": <id>}'
   ```
   Expect: reaches `gate`, ends with `rules.status='validated'` (query
   the `rules` table to confirm), and the fixture's `variants_json` is
   now populated (not NULL) for this new check_id.

9. Commit: `"Generalize fixture storage/validation to an N-variant list (no Tier 1 behavior change)"`

### Task 3: Teach `rule_compile.md` to handle multi-property (Tier 2) hypotheses

**File:** `harness/workflows/prompts/rule_compile.md`

No handler code change needed -- `rule_compile`'s journal context
already includes every column of every `hypotheses` row (via
`reads: [hypotheses, rules]` and `_read_tables`'s `SELECT *`), so the new
`property_conditions` column is already visible to the model. Only the
prompt's instructions need updating.

#### Steps:

1. Add a new section to `harness/workflows/prompts/rule_compile.md`
   (after the existing risky/safe-value negation guidance, before "Pick
   a check_id..." -- there is no "pick a check_id" section anymore per
   the deterministic-assignment pattern, so add this near the end,
   before the final JSON reply spec):
   ```
   **If the target hypothesis's `property_conditions` field is non-null**
   (a Tier 2 / combination hypothesis -- `tier` will be 2), it is a JSON
   list of `{property_path, risky_value, safe_value}` objects. The rule
   must deny only when ALL conditions are in their risky state
   simultaneously (a plain Rego rule body is an implicit AND across its
   statements, so this is just one condition per property, same syntax
   as a Tier 1 rule):

       deny contains msg if {
           some resource in input.resources
           resource.type == "<hypothesis resource_type>"
           resource.properties.<condition 1 property> == "<condition 1 risky_value>"
           resource.properties.<condition 2 property> == "<condition 2 risky_value>"
           msg := "..."
       }

   Do not use `!=`/negation tricks to combine conditions unless a
   specific condition's own semantics call for it (same guidance as
   single-property rules -- see docs/patterns/rego-rule-authoring.md).
   Every condition must be explicit; the rule must NOT fire when only
   some (not all) of the conditions are risky -- that's what the "mixed"
   fixture variants (see fixture_generate.md) exist to prove.
   ```

2. **Verify with a real, concrete Tier 2 hypothesis for Storage.** Seed
   one directly against the real journal (this is a one-off manual seed,
   the same pattern already used for the AZ-STOR-010 backfill -- see
   `docs/status/2026-07-02-status.md`):
   ```bash
   uv run --frozen python -c "
   import sys, json; sys.path.insert(0, '.')
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   conditions = [
       {'property_path': 'properties.allowSharedKeyAccess', 'risky_value': 'true', 'safe_value': 'false'},
       {'property_path': 'properties.networkAcls.defaultAction', 'risky_value': 'Allow', 'safe_value': 'Deny'},
   ]
   cur = conn.execute(
       '''INSERT INTO hypotheses
          (resource_type, property_path, rationale, source_doc, proposed_by_model,
           tier, property_conditions, status)
          VALUES (?, ?, ?, ?, ?, 2, ?, 'proposed')''',
       (
           'Microsoft.Storage/storageAccounts',
           'properties.allowSharedKeyAccess + properties.networkAcls.defaultAction',
           'Shared Key auth (a long-lived, unattributable, unscoped secret) combined with '
           'an open network ACL default means the account is reachable from any network AND '
           'accessible with a credential that cannot be scoped, rotated per-identity, or '
           'audited per-caller -- worse than either alone: Shared Key access with a locked-down '
           'network ACL at least limits the blast radius to trusted networks, and an open network '
           'ACL with Shared Key disabled at least requires Entra ID auth, which is scoped and audited.',
           'manual (Tier 2 verification hypothesis, not independently discovered)',
           'claude-opus-4-8',
           json.dumps(conditions),
       ),
   )
   conn.commit()
   print('seeded hypothesis id', cur.lastrowid)
   "
   ```
   Then compile it for real:
   ```bash
   uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml \
     --start-state rule_compile --context '{"target_hypothesis_id": <id from above>}'
   ```
   Expect: reaches `gate`. Inspect the generated `.rego` file (path from
   `rules.rule_path` for this hypothesis) and confirm it checks BOTH
   conditions with `==` (not just one). This may take a retry or two --
   that's fine, it's real LLM output; if it's rejected after 3 attempts,
   read `docs/patterns/rego-rule-authoring.md`'s general pattern and
   consider whether the fixture variants (Task 2) were generated
   correctly before concluding the prompt needs more work.

3. Commit: `"Teach rule_compile.md to combine multiple conditions for Tier 2 hypotheses"`

### Task 4: `pattern_extract` discovery handler and prompt

**Files:** `harness/engine/handlers.py`, `harness/workflows/prompts/pattern_extract.md`

#### Steps:

1. Add `apply_pattern_hypotheses` and `pattern_extract` to
   `harness/engine/handlers.py`, near `apply_schema_classifications`/
   `schema_extract` (after line 216 in the current file):
   ```python
   def apply_pattern_hypotheses(
       conn: sqlite3.Connection, proposals: list[dict[str, Any]]
   ) -> int:
       """Insert Tier 2 (combination) hypotheses. Dedup guard: skip a
       proposal whose exact set of property_paths already has a tier=2
       hypothesis for this resource_type -- there is no schema_coverage-style
       ledger for combinations (the space is too large to enumerate; see
       docs/plans/queue/2026-07-02-tier-2-pattern-checks.md), so this is the only
       dedup available. A model proposing a genuinely new but overlapping
       combination will still get through -- that's expected, not a bug.
       """
       existing_combos: dict[str, set[frozenset[str]]] = {}
       for row in conn.execute(
           "SELECT resource_type, property_conditions FROM hypotheses WHERE tier = 2"
       ):
           combo = frozenset(c["property_path"] for c in json.loads(row["property_conditions"]))
           existing_combos.setdefault(row["resource_type"], set()).add(combo)

       inserted = 0
       for item in proposals:
           resource_type = item["resource_type"]
           conditions = item["property_conditions"]
           combo = frozenset(c["property_path"] for c in conditions)
           if combo in existing_combos.get(resource_type, set()):
               continue

           conn.execute(
               """INSERT INTO hypotheses
                  (resource_type, property_path, rationale, source_doc, existing_policy_ref,
                   proposed_by_model, tier, property_conditions, status)
                  VALUES (?, ?, ?, ?, ?, ?, 2, ?, 'proposed')""",
               (
                   resource_type,
                   " + ".join(sorted(combo)),
                   item["rationale"],
                   item["source_doc"],
                   item.get("existing_policy_ref"),
                   item["proposed_by_model"],
                   json.dumps(conditions),
               ),
           )
           existing_combos.setdefault(resource_type, set()).add(combo)
           inserted += 1
       conn.commit()
       return inserted


   def pattern_extract(
       conn: sqlite3.Connection,
       state: dict[str, Any],
       context: dict[str, Any],
       raw_result: str,
   ) -> bool:
       proposals = _extract_json(raw_result)
       if isinstance(proposals, dict):
           proposals = [proposals]
       apply_pattern_hypotheses(conn, proposals)
       return True
   ```

2. Write `harness/workflows/prompts/pattern_extract.md`:
   ```
   You are proposing Tier 2 (combination/pattern) attack-path hypotheses
   for {{RESOURCE_TYPE}} -- cases where TWO OR MORE properties together
   are riskier than either is alone, even if one or both properties are
   individually fine or already covered by an existing Tier 1 check.

   Under `_files` you're given the enumerated property list and narrative/
   policy-catalog context. You're also given the current `hypotheses` table
   (including already-proposed Tier 1 AND Tier 2 hypotheses -- don't
   propose a combination that's a near-duplicate of one already there).

   This is NOT an exhaustive sweep like Tier 1's property-by-property
   classification -- the combinatorial space is too large. Instead, reason
   from real attack patterns: authentication weakened when combined with
   broadened network exposure, encryption settings that only matter given
   another setting's state, audit/logging gaps that compound with an
   access-control gap, etc. Propose 3-5 combinations you're genuinely
   confident about, each with a clear, specific rationale for why the
   combination is worse than either property alone -- not speculative
   "these could theoretically interact" hedging.

   For each combination, every property MUST be a real property_path from
   the enumerated list, and you must give a concrete risky_value/safe_value
   for each (not "any non-default value" -- pick the actual value or
   values that make it risky).

   Reply with ONLY a JSON array (no markdown fences, no prose):

       [
         {
           "resource_type": "{{RESOURCE_TYPE}}",
           "rationale": "why this SPECIFIC combination is worse than either property alone",
           "source_doc": "<repo path or URL + commit SHA from the pinned references>",
           "existing_policy_ref": "<Azure built-in Policy name, or null>",
           "proposed_by_model": "<your own model id>",
           "property_conditions": [
             {"property_path": "properties.someProperty", "risky_value": "...", "safe_value": "..."},
             {"property_path": "properties.someOtherProperty", "risky_value": "...", "safe_value": "..."}
           ]
         }
       ]
   ```
   Fill in `{{RESOURCE_TYPE}}` for Storage specifically (this file is
   Storage's `pattern_extract` prompt, same relationship as
   `schema_extract.md` -- a per-resource-type prompt, not a shared one,
   since it needs resource-specific narrative grounding).

3. Format/lint/typecheck:
   ```bash
   uv run --frozen ruff format harness/engine/handlers.py
   uv run --frozen ruff check harness/engine/handlers.py
   uv run --frozen pyright harness/engine/handlers.py
   ```
   Expect: all clean.

4. Commit: `"Add pattern_extract handler and prompt for Tier 2 discovery"`

### Task 5: `storage-pattern-tier.yaml` workflow

**File:** `harness/workflows/storage-pattern-tier.yaml`

#### Steps:

1. Create the workflow, reusing `rule_compile`/`fixture_generate`/
   `fixture_validate`/`gate` exactly as `storage-atomic-tier.yaml` does
   (they're tier-generic after Tasks 2-3) -- only `pattern_extract`
   differs from Tier 1's `schema_extract`:
   ```yaml
   # Tier-2 (pattern-check) FSM for Storage account configuration
   # hypotheses -- see docs/plans/queue/2026-07-02-tier-2-pattern-checks.md.
   # pattern_extract -> rule_compile -> fixture_generate -> fixture_validate -> gate
   workflow: storage-pattern-tier
   resource_config:
     resource_type: Microsoft.Storage/storageAccounts
     check_id_prefix: AZ-STOR-PAT
     rules_dir: rules/azure/storage
     fixtures_dir: fixtures/azure/storage
   states:
     - name: pattern_extract
       role: orchestrator
       reads: [hypotheses, schema_coverage]
       writes: [hypotheses]
       read_files:
         [
           sources/azure/storage/swagger-refs.md,
           sources/azure/storage/storage-account-properties.enumerated.json,
         ]
       prompt_template: harness/workflows/prompts/pattern_extract.md
       handler: harness.engine.handlers.pattern_extract
       next_on_success: rule_compile
       next_on_failure: end

     - name: rule_compile
       role: executor_glm
       reads: [hypotheses, rules]
       writes: [rules]
       prompt_template: harness/workflows/prompts/rule_compile.md
       handler: harness.engine.handlers.rule_compile
       next_on_success: fixture_generate
       next_on_failure: end

     - name: fixture_generate
       role: executor_glm
       reads: [rules]
       writes: [fixtures]
       prompt_template: harness/workflows/prompts/fixture_generate.md
       handler: harness.engine.handlers.fixture_generate
       next_on_success: fixture_validate
       next_on_failure: end

     - name: fixture_validate
       type: adapter
       reads: [rules, fixtures]
       writes: [runs]
       requires: [az, conftest]
       handler: harness.engine.handlers.fixture_validate
       next_on_success: gate
       next_on_failure: gate

     - name: gate
       type: gate
       reads: [runs, rules]
       writes: [rules]
       handler: harness.engine.handlers.gate
       next_on_success: end
       next_on_failure: rule_compile
   ```
   Note the `check_id_prefix: AZ-STOR-PAT` -- Tier 2 checks get their own
   numbering sequence (`AZ-STOR-PAT-001`, ...), distinct from Tier 1's
   `AZ-STOR-NNN`, so they're visually distinguishable and `_check_id_for_hypothesis`'s
   prefix-scoped numbering (already generic, no code change needed) keeps
   them from interfering with Tier 1's sequence.

2. Verify it loads:
   ```bash
   uv run --frozen python -c "
   import sys; sys.path.insert(0, '.')
   from harness.engine.runner import load_workflow
   from pathlib import Path
   wf = load_workflow(Path('harness/workflows/storage-pattern-tier.yaml'))
   print(wf['workflow'], wf['resource_config'])
   "
   ```
   Expect: prints the workflow name and resource_config with no error.

3. Commit: `"Add storage-pattern-tier.yaml workflow for Tier 2 checks"`

### Task 6: Real end-to-end verification of the full Tier 2 pipeline

**No new files** -- this task is entirely verification, using the
hypothesis seeded in Task 3 (or a fresh one via `pattern_extract` for
real, per the note below).

#### Steps:

1. If Task 3's seeded hypothesis (allowSharedKeyAccess +
   networkAcls.defaultAction) already reached `validated` during Task 3,
   skip to step 3. Otherwise finish compiling it now via
   `--start-state fixture_generate` (rule_compile already succeeded) or
   `rule_compile` again if it didn't.

2. Confirm the fixture pair actually has 2 variants (this hypothesis has
   2 conditions, so per the fixture_generate.md contract it should
   produce exactly `vulnerable`/`safe`, since "one mixed variant per
   condition" for a 2-condition hypothesis IS the same as vulnerable/safe
   plus two more -- reread the contract: for N conditions, expect
   `2 + N` variants total (all-risky, all-safe, N single-condition-risky
   mixed ones). For this 2-condition example, expect 4 variants:
   ```bash
   uv run --frozen python -c "
   import sys, json; sys.path.insert(0, '.')
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   row = conn.execute(\"SELECT variants_json FROM fixtures WHERE check_id=(SELECT check_id FROM rules WHERE hypothesis_id=<id>)\").fetchone()
   variants = json.loads(row['variants_json'])
   print(len(variants), 'variants:', [v['label'] for v in variants])
   "
   ```
   Expect: `4 variants` (or however many the model actually produced --
   if it produced only 2, that's a real finding: the fixture_generate.md
   contract update from Task 2 either wasn't followed or needs
   tightening to be more directive about the mixed-variant requirement
   for multi-condition hypotheses. Don't just accept 2 variants silently
   for a 2-condition hypothesis -- that would mean the "combination"
   claim was never actually proven).

3. Confirm the mixed variants actually behave as expected -- the rule
   should NOT fire when only one condition is risky:
   ```bash
   uv run --frozen python -c "
   import sys; sys.path.insert(0, '.')
   from harness.journal.db import connect
   from harness.adapters import bicep_validate, rego_validate
   from pathlib import Path
   import json

   conn = connect('harness/journal/harness.db')
   check_id = conn.execute('SELECT check_id FROM rules WHERE hypothesis_id=<id>').fetchone()['check_id']
   fixture_row = conn.execute('SELECT * FROM fixtures WHERE check_id=?', (check_id,)).fetchone()
   variants = json.loads(fixture_row['variants_json'])
   fixture_dir = Path(fixture_row['fixture_path'])
   policy_dir = Path('rules/azure/storage')
   for v in variants:
       label, expected = v['label'], v['expected_verdict']
       json_path = fixture_dir / f'{label}.json'
       bicep_validate.bicep_to_json(fixture_dir / f'{label}.bicep', json_path)
       result = rego_validate.validate(json_path, policy_dir, expected, check_id)
       print(label, '-> actual:', result['actual_verdict'], 'expected:', expected, 'PASS' if result['passed'] else 'FAIL')
   "
   ```
   Expect: every variant's `actual_verdict` matches `expected_verdict`,
   `PASS` on all of them -- including both mixed variants correctly
   evaluating to `pass` (rule does NOT fire), proving the rule genuinely
   requires both conditions.

4. Regression-check that this new Tier 2 check doesn't cross-contaminate
   any existing Tier 1 check sharing the same `rules/azure/storage/`
   directory (same real risk class as the cross-rule contamination bug
   from `docs/status/2026-07-01-status.md` Session 5 -- the per-check
   Rego namespace convention should already prevent it, but verify, don't
   assume):
   ```bash
   # re-run the full 41+1-rule regression check from Task 2 step 7,
   # now including the new Tier 2 check_id in the loop
   ```
   Expect: `ALL PASSED` for all checks, Tier 1 and the new Tier 2 one
   together.

5. Commit: `"Verify Tier 2 pipeline end-to-end with a real combination hypothesis"`
   (only the new rule/fixture files if not already committed in Task 3).

### Task 7: Update docs to reflect Tier 2 is now real

**Files:** `docs/operating-tiers.md`, `docs/patterns/README.md`

#### Steps:

1. In `docs/operating-tiers.md`, update the "What 'tier' means here"
   section's Tier 2 bullet from "Not implemented" to describe the actual
   implementation (discovery via `pattern_extract`, not exhaustive;
   `property_conditions` JSON column; N-variant fixtures), and add a
   "Tier 2 commands" section mirroring the existing Tier 1 command
   reference (targeting `storage-pattern-tier.yaml`).

2. Add a `docs/patterns/tier-2-combination-checks.md` if this task
   surfaced any new reusable lesson (e.g. if the mixed-variant
   verification in Task 6 step 2 found the model under-producing
   variants, that's a real pattern worth documenting the same way
   `rego-rule-authoring.md` documents the `==`-vs-`!=` lesson -- don't
   write this file speculatively if nothing new was actually learned).

3. Commit: `"Document Tier 2 in operating-tiers.md"`

## Open questions for whoever executes this plan

- **Task 4's dedup guard is weaker than Tier 1's `schema_coverage`
  ledger** (exact-combination-match only, no equivalent of "have we
  fully covered the space" since the space isn't enumerable). If
  duplicate/near-duplicate Tier 2 proposals become a real problem in
  practice, that's a new problem needing a new solution, not a sign this
  plan was wrong -- don't over-engineer a solution to it up front.
- **This plan only wires up Storage.** A second resource type wanting
  Tier 2 needs its own `pattern_extract.md` (same relationship as
  `schema_extract.md` templates -- see `docs/onboarding-new-resource-type.md`)
  and its own `<slug>-pattern-tier.yaml`. Not automated by
  `bootstrap_resource_type.py` in this plan; a natural follow-up once
  Tier 2 exists for at least one resource type to generalize from.
