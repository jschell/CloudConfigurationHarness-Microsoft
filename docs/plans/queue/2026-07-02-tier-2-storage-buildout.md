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
4. **Parallelism: yes for verification, no for discovery/compilation.**
   Discovery (Task 2) and compilation (Task 3) stay sequential -- both
   write to the shared SQLite journal (`db.py` opens no WAL mode, no
   `busy_timeout`), and `_check_id_for_hypothesis` does a non-atomic
   read-then-write, so concurrent `pattern_extract`/`rule_compile`
   calls risk the exact check_id collision this project already found
   and fixed once for sequential runs. Task 4's regression check is
   the opposite case: read-only against the journal, and each
   check_id's work touches only its own files, so it's safe to fan out
   across threads for a real speedup with no race risk -- see Task 4.

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

### Task 4: Full regression check across every rule, Tier 1 and Tier 2 together (parallel)

**File:** `harness/tools/regression_check.py` (new) -- promotes the
ad-hoc snippet from `docs/operating-tiers.md`'s "Regression-check the
whole rule set for real" section into a real, reusable, parallel tool.

**Why this one is safe to parallelize when Tasks 2-3 are not:** this
task only *reads* the journal (no `INSERT`/`UPDATE`) and each
check_id's work -- compile its own `.bicep` fixtures to its own
`.json` files, run `conftest` against its own rule's namespace -- never
touches another check_id's files or rows. There's no shared mutable
state for two workers to race on, unlike `_check_id_for_hypothesis`'s
non-atomic read-then-write (see the Tier 2 plan's warning and the
answer given when this parallelization was discussed: don't parallelize
`pattern_extract`/`rule_compile`/`fixture_generate` against the shared
SQLite journal -- `db.py` opens no WAL mode and no `busy_timeout`, so
concurrent writers hit `database is locked` or silently race the
check_id counter).

Threads, not processes: each unit of work is dominated by waiting on
`az`/`conftest` subprocess calls (I/O-bound), so `ThreadPoolExecutor`
gets the parallelism without inter-process SQLite/state-sharing
complexity `ProcessPoolExecutor` would add for zero benefit here.

#### Steps:

1. Verify the gap first -- confirm no such tool exists yet:
   ```bash
   ls harness/tools/regression_check.py 2>&1
   ```
   Expect: `No such file or directory`.

2. Write `harness/tools/regression_check.py`:
   ```python
   """Regression-check every rule/fixture pair in the journal for real,
   in parallel. Promotes the ad-hoc snippet from
   docs/operating-tiers.md's "Regression-check the whole rule set for
   real" section into a reusable tool.

   Safe to parallelize (unlike pattern_extract/rule_compile/
   fixture_generate against the shared journal -- see
   docs/plans/queue/2026-07-02-tier-2-storage-buildout.md's Task 4):
   this tool only reads the journal, and each check_id's work (compile
   its own fixtures, run conftest against its own rule) touches only
   files scoped to that check_id, so there's nothing for two workers to
   race on. Threads, not processes, since the work is I/O-bound
   (waiting on az/conftest subprocesses), not CPU-bound.

   Usage:
       python -m harness.tools.regression_check
       python -m harness.tools.regression_check --resource-dir rules/azure/storage --workers 8
   """

   from __future__ import annotations

   import argparse
   import json
   from concurrent.futures import ThreadPoolExecutor, as_completed
   from pathlib import Path
   from typing import Any

   from harness.adapters import bicep_validate, rego_validate
   from harness.journal.db import connect

   DEFAULT_WORKERS = 8


   def _check_one(check_id: str, fixture_path: str, variants_json: str | None, policy_dir: Path) -> list[dict[str, Any]]:
       fixture_dir = Path(fixture_path)
       variants = (
           json.loads(variants_json)
           if variants_json
           else [
               {"label": "vulnerable", "expected_verdict": "fail"},
               {"label": "safe", "expected_verdict": "pass"},
           ]
       )
       results = []
       for v in variants:
           label, expected = v["label"], v["expected_verdict"]
           json_path = fixture_dir / f"{label}.json"
           bicep_validate.bicep_to_json(fixture_dir / f"{label}.bicep", json_path)
           result = rego_validate.validate(json_path, policy_dir, expected, check_id)
           results.append({"check_id": check_id, "label": label, **result})
       return results


   def run(db_path: Path | str | None, policy_dir: Path, workers: int) -> bool:
       conn = connect(db_path) if db_path else connect()
       rows = conn.execute(
           """SELECT r.check_id, f.fixture_path, f.variants_json
              FROM rules r JOIN fixtures f ON r.check_id = f.check_id
              ORDER BY r.check_id"""
       ).fetchall()
       print(f"checking {len(rows)} rules with {workers} workers")

       all_ok = True
       with ThreadPoolExecutor(max_workers=workers) as pool:
           futures = {
               pool.submit(_check_one, r["check_id"], r["fixture_path"], r["variants_json"], policy_dir): r["check_id"]
               for r in rows
           }
           for future in as_completed(futures):
               check_id = futures[future]
               try:
                   results = future.result()
               except Exception as exc:  # noqa: BLE001 -- surface any adapter error per check_id
                   print(f"{check_id}: ERROR {exc}")
                   all_ok = False
                   continue
               for result in results:
                   if not result["passed"]:
                       all_ok = False
                       print(f"{result['check_id']} {result['label']} -> FAIL {result}")

       print("ALL PASSED" if all_ok else "SOME FAILED")
       return all_ok


   def main() -> int:
       parser = argparse.ArgumentParser(description=__doc__)
       parser.add_argument("--db", type=Path, default=None)
       parser.add_argument("--policy-dir", type=Path, default=Path("rules/azure/storage"))
       parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
       args = parser.parse_args()
       ok = run(args.db, args.policy_dir, args.workers)
       return 0 if ok else 1


   if __name__ == "__main__":
       raise SystemExit(main())
   ```

   Note the join changed from the ad-hoc snippet's `rules` ->
   `fixtures` lookup-per-row to a single `JOIN` query -- same data,
   one round trip instead of N, and it means the SQLite connection is
   only ever touched from the main thread (each worker thread gets
   plain file I/O and subprocess calls, no `sqlite3.Connection` object
   crossing threads -- `sqlite3` connections are not thread-safe by
   default, so this avoids that hazard entirely rather than needing a
   per-thread connection).

3. Format/lint/typecheck:
   ```bash
   uv run --frozen ruff format harness/tools/regression_check.py
   uv run --frozen ruff check harness/tools/regression_check.py
   uv run --frozen pyright harness/tools/regression_check.py
   ```
   Expect: all clean.

4. Run it against the real journal and compare timing against the old
   sequential snippet to confirm the parallelism is actually paying
   for itself (if `az`/`conftest` startup overhead dominates at this
   rule count, that's a real finding worth noting in Task 5, not a
   reason to silently keep the tool anyway):
   ```bash
   uv run --frozen python -m harness.tools.regression_check
   ```
   Expect: `checking <42 + N validated> rules` then `ALL PASSED`, where
   `N` is however many new Tier 2 checks reached `validated` in Task 3
   (rejected checks still have a `rules` row and fixtures, and SHOULD
   still pass this loop -- "rejected" means the gate's retries were
   exhausted while runs still failed, not that the fixture/rule pairing
   on disk right now is inconsistent. If a rejected check's fixtures
   don't validate against its own rule here, re-read
   `docs/patterns/rego-rule-authoring.md` before assuming it's this
   plan's bug).

5. If anything fails, do not proceed to Task 5 -- diagnose using the
   same process as the original Tier 2 plan (check namespace
   contamination first, per
   `docs/patterns/deterministic-check-id-assignment.md`, then the
   `==`-vs-`!=` guidance in `docs/patterns/rego-rule-authoring.md`).
   `--workers 1` reproduces the old strictly-sequential behavior if
   parallelism itself is ever suspected of causing a spurious failure
   (it shouldn't, given the independence argument above, but ruling it
   out is one flag away).

6. Also replace the stale sequential snippet in
   `docs/operating-tiers.md`'s "Regression-check the whole rule set for
   real" section with a pointer to this tool, so the docs don't keep
   two copies of the same logic to maintain:
   ```
   ### Regression-check the whole rule set for real

   ```bash
   uv run --frozen python -m harness.tools.regression_check
   ```

   Parallel (`ThreadPoolExecutor`, I/O-bound on `az`/`conftest`
   subprocess calls) and safe to parallelize because it's read-only
   against the journal and each check_id's work touches only its own
   files -- see `harness/tools/regression_check.py`'s module docstring.
   Use `--workers 1` to reproduce strictly-sequential behavior, or
   `--policy-dir`/`--db` to point at a different resource type's rules
   or a scratch journal.
   ```

7. Commit: `"Add parallel regression_check.py tool, replacing the ad-hoc sequential snippet"`

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
