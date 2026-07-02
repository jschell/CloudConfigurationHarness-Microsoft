# Feature: Build out Tier 2 (pattern) checks for Storage

## Goal

Go from "Tier 2 pipeline proven with one manually-seeded hypothesis
(`AZ-STOR-042`)" to "Tier 2 has a real, LLM-discovered set of validated
combination checks for Storage" -- by running `pattern_extract` for
real discovery and batch-compiling whatever it proposes, after closing
a real gap in the batch-compile tool that would otherwise let a Tier 1
and Tier 2 hypothesis collide under the wrong check_id prefix.

## Architecture

Nothing new to design -- `docs/plans/complete/2026-07-02-tier-2-pattern-checks.md`
already built the whole pipeline (`pattern_extract -> rule_compile ->
fixture_generate -> fixture_validate -> gate`, `storage-pattern-tier.yaml`,
N-variant fixtures). This plan just *uses* it for real, plus one fix
that surfaced while reviewing the tooling for that use:

1. **`harness/tools/run_hypothesis_buildout.py`'s `remaining_hypothesis_ids`
   filters only by `resource_type`, not `tier`.** Both
   `storage-atomic-tier.yaml` and `storage-pattern-tier.yaml` share the
   same `resource_type` (`Microsoft.Storage/storageAccounts`), so if an
   uncompiled Tier 1 hypothesis and a new Tier 2 hypothesis ever exist
   in the journal at the same time, pointing the buildout tool at
   `storage-pattern-tier.yaml` would compile *both* under the
   `AZ-STOR-PAT` prefix (and vice versa for the atomic workflow) --
   silently misfiling a check's tier and its check_id sequence. There
   are no orphaned hypotheses in the journal today (verified: 42
   hypotheses, 42 rules, zero uncompiled), so it hasn't bitten yet, but
   running `pattern_extract` in Task 2 below is exactly the situation
   that creates the risk (new Tier 2 hypotheses will exist alongside
   whatever Tier 1 backlog exists at the time). Fix this before
   depending on it.
2. **Discovery.** `pattern_extract` isn't exhaustive by design (the
   combinatorial space is too large -- see the Tier 2 plan's
   Architecture section) -- it proposes a handful of plausible
   combinations per call, reasoning from attack patterns, deduped on
   exact property-path-set match. There's no completeness ledger
   (Tier 1's `schema_coverage` has no Tier 2 equivalent), so "done" is
   judged empirically: call it repeatedly until a couple of consecutive
   calls add nothing new, not against a fixed target count.
3. **Compilation.** Once fixed, `run_hypothesis_buildout.py --workflow
   storage-pattern-tier.yaml` needs no further changes -- it already
   drives the shared `rule_compile -> fixture_generate ->
   fixture_validate -> gate` states per hypothesis, same as Tier 1.

## Tech Stack

Same as the rest of the harness: Python 3.11, SQLite, YAML workflow
definitions, `az bicep build` + `conftest` as the deterministic
verifier. **No automated test suite exists in this repo** -- every task
here is a real end-to-end run against the live journal and real
`az`/`conftest`/model APIs, matching how every prior task in this
project was actually verified (see `docs/status/*.md` and the Tier 2
plan). Where a step says "verify," that means running the real command
and reading its real output, not writing a mock.

**Environment reminders** (see `docs/operating-tiers.md`): export
`UV_LINK_MODE=copy`; prepend
`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin` to `PATH` if `az`
reports MISS; **never run `rule_compile`/`fixture_generate` against a
scratch `--db` without first seeding it with dummy rows for every real
check_id already in use** (file writes are `REPO_ROOT`-relative
regardless of `--db`). This plan operates entirely against the real
journal (`harness/journal/harness.db`), not a scratch one, so that
hazard shouldn't come up -- but don't introduce a scratch `--db` run
without rereading that warning first.

## Tasks

### Task 1: Filter `run_hypothesis_buildout.py` by tier, not just resource_type

**Files:** `harness/workflows/storage-atomic-tier.yaml`,
`harness/workflows/storage-pattern-tier.yaml`,
`harness/tools/run_hypothesis_buildout.py`

#### Steps:

1. Verify the gap first -- confirm the current query has no tier
   filter:
   ```bash
   grep -n "remaining_hypothesis_ids" -A 10 harness/tools/run_hypothesis_buildout.py
   ```
   Expect to see `SELECT id FROM hypotheses WHERE resource_type = ?`
   with no `tier` condition.

2. Add an explicit `tier` field to each workflow's `resource_config`
   block, so the tool doesn't have to infer it from `check_id_prefix`
   string-matching (fragile) or from which discovery state the
   workflow happens to have (indirect). In
   `harness/workflows/storage-atomic-tier.yaml`, in the
   `resource_config:` block (currently 4 keys: `resource_type`,
   `check_id_prefix`, `rules_dir`, `fixtures_dir`):
   ```yaml
   resource_config:
     resource_type: Microsoft.Storage/storageAccounts
     tier: 1
     check_id_prefix: AZ-STOR
     rules_dir: rules/azure/storage
     fixtures_dir: fixtures/azure/storage
   ```
   And in `harness/workflows/storage-pattern-tier.yaml`'s
   `resource_config:` block:
   ```yaml
   resource_config:
     resource_type: Microsoft.Storage/storageAccounts
     tier: 2
     check_id_prefix: AZ-STOR-PAT
     rules_dir: rules/azure/storage
     fixtures_dir: fixtures/azure/storage
   ```

3. In `harness/engine/handlers.py`, `_resource_config` (around line 51)
   only requires the dict be present/truthy -- it doesn't validate
   individual keys, so adding `tier` needs no change there.
   `rule_compile`/`fixture_generate` read specific keys by name and
   ignore unknown ones, so the new `tier` key is inert for them. No
   code change needed in `handlers.py` for this step -- confirm by
   rereading `_resource_config` and `rule_compile`/`fixture_generate`
   to make sure neither does something like iterate all keys
   positionally (they don't; they use `config["check_id_prefix"]` etc.
   by name).

4. In `harness/tools/run_hypothesis_buildout.py`, update
   `remaining_hypothesis_ids` (lines 44-55) to accept and filter by
   `tier`:
   ```python
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
   ```

5. Update `run()` (lines 58-113) to read `tier` from the workflow's
   `resource_config` and pass it through. Replace:
   ```python
       workflow = load_workflow(workflow_path)
       resource_type = workflow["resource_config"]["resource_type"]

       runner = Runner(db_path=db_path, role_override=role_override or {})
       conn = runner.conn
       ids = remaining_hypothesis_ids(conn, resource_type)
       print(f"{len(ids)} hypotheses remaining to compile for {resource_type}: {ids}")
   ```
   with:
   ```python
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
   ```
   Using `workflow["resource_config"]["tier"]` (not `.get(..., 1)`)
   deliberately makes a workflow YAML missing `tier` a hard `KeyError`
   at buildout time rather than a silent default to 1 -- a workflow
   author forgetting to declare its tier should find out immediately,
   not have it quietly misclassified.

6. Format/lint/typecheck:
   ```bash
   uv run --frozen ruff format harness/tools/run_hypothesis_buildout.py
   uv run --frozen ruff check harness/tools/run_hypothesis_buildout.py
   uv run --frozen pyright harness/tools/run_hypothesis_buildout.py
   ```
   Expect: all clean.

7. Verify both workflows still load and expose the new field:
   ```bash
   uv run --frozen python -c "
   from harness.engine.runner import load_workflow
   from pathlib import Path
   for p in ['harness/workflows/storage-atomic-tier.yaml', 'harness/workflows/storage-pattern-tier.yaml']:
       wf = load_workflow(Path(p))
       print(p, '->', wf['resource_config'])
   "
   ```
   Expect: each prints its `resource_config` including `'tier': 1` or
   `'tier': 2` respectively.

8. Verify the buildout tool now reports zero remaining hypotheses for
   both tiers against the real journal (sanity check the filter change
   didn't break the "already fully compiled" case):
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   from harness.tools.run_hypothesis_buildout import remaining_hypothesis_ids
   conn = connect('harness/journal/harness.db')
   print('tier 1 remaining:', remaining_hypothesis_ids(conn, 'Microsoft.Storage/storageAccounts', 1))
   print('tier 2 remaining:', remaining_hypothesis_ids(conn, 'Microsoft.Storage/storageAccounts', 2))
   "
   ```
   Expect: both print `[]`.

9. Commit: `"Filter run_hypothesis_buildout.py by tier, not just resource_type"`

### Task 2: Run `pattern_extract` for real, repeatedly, until it stops finding new combinations

**No new files** -- this task is real LLM-driven discovery against the
live journal.

#### Steps:

1. Record the current Tier 2 hypothesis count as a baseline:
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   print(conn.execute(\"SELECT COUNT(*) c FROM hypotheses WHERE tier = 2\").fetchone()['c'])
   "
   ```
   Expect: `1` (just `AZ-STOR-042`'s hypothesis from the prior plan).

2. Run `pattern_extract` for real:
   ```bash
   uv run --frozen python -m harness.engine.runner harness/workflows/storage-pattern-tier.yaml
   ```
   This runs the full FSM starting at `pattern_extract`, which will
   also immediately try to `rule_compile`/`fixture_generate`/
   `fixture_validate`/`gate` whatever it just proposed (the workflow
   doesn't stop after discovery) -- that's fine and is exactly Task 3's
   job pulled forward for this one call's proposals; no separate
   "discovery only" mode exists, matching how `schema_extract` is also
   never run standalone in Tier 1.

3. Check how many new Tier 2 hypotheses exist and what they are:
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   rows = conn.execute(\"SELECT id, property_path, rationale FROM hypotheses WHERE tier = 2 ORDER BY id\").fetchall()
   print(len(rows), 'total tier-2 hypotheses')
   for r in rows:
       print(r['id'], '-', r['property_path'])
   "
   ```
   Expect: more than 1 now (the model proposes 3-5 per call per
   `pattern_extract.md`).

4. Repeat step 2 two or three more times (each is a fresh, independent
   `pattern_extract` call against the now-larger `hypotheses` context,
   so it sees its own prior proposals and Task 1's dedup guard skips
   any exact-combination repeat). After each run, rerun step 3's query.
   Track the count after each call:
   ```
   after call 1: <n1>
   after call 2: <n2>
   after call 3: <n3>
   after call 4: <n4>
   ```
   Stop once two consecutive calls add zero new hypotheses (the model
   has converged on repeating combinations it already proposed), or
   after 5 calls total, whichever comes first -- don't call it in an
   unbounded loop chasing marginal, increasingly-speculative
   combinations; `pattern_extract.md` already asks for "genuinely
   confident" ones, not exhaustive brainstorming.

5. For each Tier 2 hypothesis, spot-check that `property_conditions`
   holds real, distinct property paths (not the model hallucinating a
   property that isn't in
   `sources/azure/storage/storage-account-properties.enumerated.json`):
   ```bash
   uv run --frozen python -c "
   import json
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   enumerated = {p['name'] for p in json.load(open('sources/azure/storage/storage-account-properties.enumerated.json'))}
   for r in conn.execute(\"SELECT id, property_conditions FROM hypotheses WHERE tier = 2\"):
       conditions = json.loads(r['property_conditions'])
       for c in conditions:
           prop = c['property_path'].removeprefix('properties.')
           if prop not in enumerated:
               print('hypothesis', r['id'], 'references unknown property:', c['property_path'])
   print('spot-check done')
   "
   ```
   (Adjust the property-name extraction to match the enumerated file's
   actual JSON shape -- check it with a quick `head`/`python -m json.tool`
   first if the key names above don't match; this file's exact schema
   was established by `harness/tools/enumerate_schema_properties.py`
   in the original plan and may nest differently than a flat `name`
   key.) Expect: no output besides `spot-check done`. If it finds a
   hallucinated property, that's a real finding -- flag it in the
   status writeup for Task 5, don't silently drop the hypothesis (its
   `rule_compile` attempt will likely just fail validation and get
   `rejected`, which is an acceptable outcome, but worth noting as a
   `pattern_extract.md` prompt-quality signal either way).

6. No commit for this task by itself -- rule/fixture files land as a
   side effect of `pattern_extract`'s workflow run continuing through
   `rule_compile`/`fixture_generate`, and get committed together with
   Task 3's cleanup pass (some may still be `draft`/mid-retry after
   this task; Task 3 finishes any stragglers and commits the whole
   batch).

### Task 3: Batch-compile every remaining Tier 2 hypothesis

**No new files.**

#### Steps:

1. Check whether anything is still uncompiled after Task 2's runs
   (some hypotheses may not have made it through `rule_compile` yet
   if a run's fixture validation used up retries mid-batch, or if
   `pattern_extract` proposed more in one call than the FSM had time to
   compile before `end`):
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   from harness.tools.run_hypothesis_buildout import remaining_hypothesis_ids
   conn = connect('harness/journal/harness.db')
   print(remaining_hypothesis_ids(conn, 'Microsoft.Storage/storageAccounts', 2))
   "
   ```

2. If the list is non-empty, compile the rest:
   ```bash
   uv run --frozen python -m harness.tools.run_hypothesis_buildout --workflow harness/workflows/storage-pattern-tier.yaml
   ```
   Expect: one `=== hypothesis <id> ===` block per remaining ID,
   ending in either `AZ-STOR-PAT-NNN: validated` or
   `AZ-STOR-PAT-NNN: rejected` for each (both are legitimate FSM
   outcomes -- see the module's own docstring on why `rejected` isn't a
   failure of this tool).

3. Query the final state of every Tier 2 rule:
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   for r in conn.execute(\"\"\"
       SELECT r.check_id, r.status, h.property_path
       FROM rules r JOIN hypotheses h ON r.hypothesis_id = h.id
       WHERE h.tier = 2 ORDER BY r.check_id
   \"\"\"):
       print(dict(r))
   "
   ```
   Record the counts of `validated` vs `rejected` for the status
   writeup in Task 5 -- a `rejected` Tier 2 check is not a bug to fix
   in this plan (same as Tier 1's precedent), just a hypothesis that
   didn't compile to a provable rule in 3 attempts.

4. Commit whatever's new on disk (rules + fixtures for every Tier 2
   check compiled across Tasks 2-3):
   ```bash
   git add rules/azure/storage/AZ-STOR-PAT-*.rego fixtures/azure/storage/AZ-STOR-PAT-*
   git status --short   # confirm nothing unexpected is staged
   git commit -m "Build out Tier 2 combination checks for Storage via pattern_extract"
   ```

### Task 4: Full regression check across every rule, Tier 1 and Tier 2 together

**No new files** -- reuses the variants-aware regression snippet from
`docs/operating-tiers.md`'s "Regression-check the whole rule set for
real" section (added when N-variant fixtures were introduced).

#### Steps:

1. Run it against the real journal:
   ```bash
   uv run --frozen python -c "
   import json
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
       fixture_row = conn.execute('SELECT variants_json FROM fixtures WHERE check_id=?', (check_id,)).fetchone()
       fixture_dir = Path(f'fixtures/azure/storage/{check_id}')
       variants = json.loads(fixture_row['variants_json']) if fixture_row['variants_json'] else [
           {'label': 'vulnerable', 'expected_verdict': 'fail'},
           {'label': 'safe', 'expected_verdict': 'pass'},
       ]
       for v in variants:
           label, expected = v['label'], v['expected_verdict']
           json_path = fixture_dir / f'{label}.json'
           bicep_validate.bicep_to_json(fixture_dir / f'{label}.bicep', json_path)
           result = rego_validate.validate(json_path, policy_dir, expected, check_id)
           all_ok &= result['passed']
           if not result['passed']:
               print(check_id, label, '-> FAIL', result)
   print('ALL PASSED' if all_ok else 'SOME FAILED')
   "
   ```
   Expect: `checking <42 + N validated> rules` then `ALL PASSED`, where
   `N` is however many new Tier 2 checks reached `validated` in Task 3
   (this count naturally excludes `rejected` ones, since those never
   got a `rules` row... actually they do get a `rules` row with
   `status='rejected'` -- rejected rules still have fixtures and still
   get checked here, and SHOULD still pass this loop, since "rejected"
   means the gate's retries were exhausted while runs still failed, not
   that the fixture/rule pairing is inconsistent with what's on disk
   right now. If a rejected check's fixtures don't validate against
   its own rule here, re-read `docs/patterns/rego-rule-authoring.md`
   before assuming it's this plan's bug).

2. If anything fails, do not proceed to Task 5 -- diagnose using the
   same process as the original Tier 2 plan (check namespace
   contamination first, per
   `docs/patterns/deterministic-check-id-assignment.md`, then the
   `==`-vs-`!=` guidance in `docs/patterns/rego-rule-authoring.md`).

3. No commit -- this task is pure verification.

### Task 5: Update docs with the real Tier 2 check count and any new lesson

**Files:** `docs/operating-tiers.md`, `docs/patterns/README.md` (only if warranted)

#### Steps:

1. In `docs/operating-tiers.md`'s Tier 2 bullet (added by the prior
   plan's Task 7), update the example to reference the real, current
   set of Tier 2 checks instead of only `AZ-STOR-042` -- e.g. change
   "proven live as `AZ-STOR-042`" to name a couple of the new checks
   too, or generalize the sentence to "N Tier 2 checks live for
   Storage as of <date>" without hardcoding a count that will drift.
   Prefer the latter (a specific number in prose rotted the "40 vs 41
   checks" confusion earlier in this project's history -- see
   `docs/status/2026-07-02-status.md` -- don't reintroduce that
   failure mode).

2. Add a `docs/patterns/tier-2-combination-checks.md` **only if** Task
   2's spot-check (step 5) or Task 3's compile pass surfaced something
   genuinely reusable -- e.g. if the model systematically
   under-proposed combinations, hallucinated properties at a
   noteworthy rate, or a specific category of combination reliably got
   `rejected` for a fixable prompt reason. Do not write this file
   speculatively if the buildout went cleanly; the prior plan's Task 7
   made the same call and correctly didn't write one.

3. Commit: `"Update operating-tiers.md with Tier 2 buildout results"`
   (or a more specific message if a patterns doc was also added).

## Open questions for whoever executes this plan

- **How many `pattern_extract` calls is "enough"?** Task 2 caps at 5
  calls or two consecutive empty ones, whichever first, as a pragmatic
  default -- if the model is still finding genuinely distinct,
  well-reasoned combinations at call 5, that's a signal to keep going
  past this plan's cap, not a hard stop. Use judgment; don't treat 5 as
  sacred.
- **This only builds out Storage.** Extending Tier 2 discovery to a
  second resource type needs that resource type's own
  `pattern_extract.md` (or, if the current one turns out to generalize
  cleanly once resource-type placeholders are added, a shared
  template) -- not in scope here, flagged the same way the original
  Tier 2 plan flagged it.
