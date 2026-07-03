# Operating the harness: tiers, commands, and what's actually built

## What "tier" means here

`hypotheses.tier` (see `harness/journal/schema.sql`) has three defined
values, from the original design:

- **Tier 1 (atomic)** -- a single property on a single resource is
  risky or safe on its own (e.g. `networkAcls.defaultAction == "Allow"`).
  `schema_extract`, `rule_compile`, `fixture_generate`, the whole
  `storage-atomic-tier.yaml` FSM.
- **Tier 2 (pattern)** -- a *combination* of properties on one resource
  is risky even though no single property is, by itself (e.g.
  `allowSharedKeyAccess == true` combined with
  `networkAcls.defaultAction == "Allow"`, proven live as `AZ-STOR-042`).
  **Implemented** (see
  `docs/plans/active/2026-07-02-tier-2-pattern-checks.md` for the
  design): `pattern_extract` proposes a
  handful of plausible combinations reasoning from known attack
  patterns -- NOT an exhaustive sweep like Tier 1's `schema_coverage`
  (even just pairs of Storage's ~72 writable properties is ~2,500
  combinations, too many to classify one by one). A hypothesis's
  `property_conditions` column (JSON list of
  `{property_path, risky_value, safe_value}`) holds the combination;
  `property_path`/`risky_value`/`safe_value` stay NULL/summary-only for
  tier>=2 rows. `rule_compile`/`fixture_generate`/`fixture_validate`/
  `gate` are unchanged code paths, generic across tiers: fixtures are
  an N-variant list (`fixtures.variants_json`) instead of a fixed
  vulnerable/safe pair, so a combination hypothesis can be proven with
  an all-risky variant, an all-safe variant, and one "mixed" variant per
  condition (only that one condition risky) showing the rule doesn't
  fire on any single property in isolation. Tier 1 rows keep
  `variants_json IS NULL` and fall back to the original two-variant
  shape -- no existing rule/fixture changed behavior.
- **Tier 3 (chained)** -- risk emerges from a relationship *across*
  resources (e.g. a storage account's network rules combined with a
  peered VNet's routing). Not implemented; not designed yet either. This
  was an explicit non-goal for the initial phase (see
  `docs/plans/complete/multi-model-config-discovery.md`).

If you're asked to add a "combination" or "cross-resource" check, that's
new design work, not a parameter to flip on the existing pipeline.

## The Tier 1 / Tier 2 pipeline, end to end

```
schema_extract (LLM, Tier 1) or pattern_extract (LLM, Tier 2) -> hypotheses[, schema_coverage]
  -> rule_compile (LLM) -> rules (status=draft)
  -> fixture_generate (LLM) -> fixtures (N-variant list)
  -> fixture_validate (deterministic: az bicep build + conftest) -> runs (one row per variant)
  -> gate (pure logic): pass -> rules (status=validated) / fail -> retry rule_compile (max 3x) -> rules (status=rejected)
```

`rule_compile`/`fixture_generate`/`fixture_validate`/`gate` are the same
code and the same handler functions for both tiers -- only the
discovery state (`schema_extract` vs `pattern_extract`) and the prompt
templates differ. Tier 1's `storage-atomic-tier.yaml` and Tier 2's
`storage-pattern-tier.yaml` both wire up the shared four states, with
`check_id_prefix` (`AZ-STOR` vs `AZ-STOR-PAT`) keeping the two numbering
sequences distinct.

Every state's `role`/`type`, `reads`/`writes`, and (for adapter states)
`requires` are declared in the workflow YAML, not hardcoded in Python.
`harness/engine/handlers.py` is generic across resource types via each
workflow's `resource_config` block (`check_id_prefix`, `rules_dir`,
`fixtures_dir`, `resource_type`) -- see
[onboarding-new-resource-type.md](onboarding-new-resource-type.md).

## Environment setup (once per shell)

```bash
uv sync
export UV_LINK_MODE=copy   # only if the repo lives on a filesystem without hardlink support
# on this Windows machine specifically, az isn't on PATH by default:
export PATH="/c/Program Files/Microsoft SDKs/Azure/CLI2/wbin:$PATH"
```

Always check tools are present before a real run:

```bash
uv run --frozen python -m harness.engine.preflight harness/workflows/storage-atomic-tier.yaml
```

## A real hazard: `--db` does NOT isolate file writes

`rule_compile`/`fixture_generate` write `.rego`/`.bicep` files to paths
under the repo root (`REPO_ROOT / rules_dir / check_id.rego`, etc.),
computed from the **journal's own contents**, not from anything
scoped to `--db`. If you point a scratch/experimental `--db` at an
otherwise-empty database and run `rule_compile`, `_check_id_for_hypothesis`
sees no existing rows in *that* database and confidently assigns
`AZ-STOR-001` -- which silently overwrites the real, committed
`rules/azure/storage/AZ-STOR-001.rego` on disk, because the file path
is real regardless of which `--db` you used. This happened for real
while verifying the `resource_config` generalization (2026-07-02) and
was caught immediately via `git status`/`git checkout` before being
committed.

**Before running `rule_compile`/`fixture_generate` against a scratch
`--db`, seed it with dummy `rules` rows matching every real check_id
already in use**, so the scratch database's own numbering logic skips
past them and lands on a number that has no corresponding real file.
Or, safer still: don't test `rule_compile`/`fixture_generate` against a
scratch DB at all -- test `_check_id_for_hypothesis` directly (it's pure,
no file I/O), and reserve full end-to-end runs for the real journal
where check_id collisions are actually prevented by design.

## Sharing one journal across worktrees

`harness/journal/harness.db` is gitignored -- it's operational state,
not code, so a git worktree branching off `main` does **not** get a
copy of it the way it gets a copy of every tracked file. Two different
plans (Tier 2 Storage buildout and KeyVault Tier 1 onboarding) were
executed concurrently in separate worktrees this way (2026-07-02) and
diverged for real: one session copied the journal into its worktree at
setup and kept writing to that local copy, while the other passed
`--db` pointing at main's journal directly. Main ended up with 8 new
KeyVault rules the copied worktree didn't have; the copied worktree
ended up with 9 new Storage Tier 2 rules main didn't have. Reconciling
required a one-off script reinserting the missing rows with freshly
assigned autoincrement IDs (remapping every foreign key reference) --
recoverable because nothing was silently overwritten (`INSERT`, not
`UPDATE`, and check_id prefixes never collided between the two), but
not something to depend on repeating cleanly.

**Don't copy `harness/journal/harness.db` into a new worktree.** Point
every workflow/tool invocation's `--db` at the one real file instead
(relative path from a worktree under `.worktrees/<name>/`:
`--db ../../harness/journal/harness.db`). The journal stays centralized
and single-sourced; only the `.rego`/`.bicep` files stay git-isolated
per worktree (by design -- see the hazard above and
`docs/patterns/deterministic-check-id-assignment.md`), to be merged
into `main` through the normal git merge when a worktree's branch is
done, not by hand-copying files across worktrees.

This does not make truly *simultaneous* writes safe -- `db.py` opens
no WAL mode and no `busy_timeout`, and `_check_id_for_hypothesis` still
does a non-atomic read-then-write, so two `rule_compile` calls against
the same shared file at the literal same instant can still race or hit
`database is locked`. Sharing one file only solves the fork-and-merge
problem; avoiding the concurrent-write problem is still a procedural
discipline (don't run two LLM-writing states against the same journal
at the same moment), not something the code enforces.

## Commands

All commands below default to the real, persistent journal
(`harness/journal/harness.db`) unless `--db <path>` is given. Use an
explicit scratch `--db` for throwaway/experimental runs so they don't
pollute the real journal.

### Run the full pipeline, unseeded

Lets `schema_extract` propose whatever it finds, then compiles/validates
one of the resulting hypotheses. Not safe against check_id collisions if
run concurrently with another compile (see
`docs/patterns/deterministic-check-id-assignment.md` -- collisions are
fixed at the handler level now, but `rule_compile` still picks *some*
hypothesis on its own when run this way):

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml
```

### Target a specific hypothesis

Skips `schema_extract`, jumps straight to compiling a known hypothesis
ID (see `hypotheses` table for IDs):

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml \
  --start-state rule_compile --context '{"target_hypothesis_id": 6}'
```

### A/B a hypothesis against a different model

`--role-override <declared_role>=<roles.yaml entry>` remaps a role for
this one invocation without touching the workflow YAML or `roles.yaml`.
`rule_compile`/`fixture_generate` currently default to `executor_glm`;
to compare against Claude for one hypothesis:

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml \
  --start-state rule_compile --context '{"target_hypothesis_id": 6}' \
  --role-override executor_glm=executor_claude
```

Then diff the two resulting `workflow_runs` rows:

```bash
uv run --frozen python -m harness.engine.compare_runs --run-a <id> --run-b <id>
```

### Resume an interrupted run

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml --resume <workflow_runs.id>
```

### Batch-classify every remaining property for structured discovery

The exhaustive, non-repeating, know-when-you're-done sweep (see
`docs/patterns/schema-coverage-discovery.md`) -- classifies every
property in an enumerated list not yet in `schema_coverage`, in small
batches, independent of the FSM:

```bash
uv run --frozen python -m harness.tools.run_schema_coverage \
  sources/azure/storage/storage-account-properties.enumerated.json \
  "Microsoft.Storage/storageAccounts" \
  --extra-file sources/azure/storage/swagger-refs.md \
  --batch-size 10
```

Check completion:

```bash
uv run --frozen python -m harness.tools.coverage_status \
  sources/azure/storage/storage-account-properties.enumerated.json \
  "Microsoft.Storage/storageAccounts"
```

### Batch-compile every hypothesis that doesn't have a rule yet

Runs `rule_compile -> fixture_generate -> fixture_validate -> gate` for
every uncompiled hypothesis belonging to a workflow's `resource_type`,
one at a time, with per-hypothesis retry on transient infrastructure
errors (not on genuine rule rejection -- see the module docstring):

```bash
uv run --frozen python -m harness.tools.run_hypothesis_buildout
# or, for a different resource type's workflow:
uv run --frozen python -m harness.tools.run_hypothesis_buildout --workflow harness/workflows/<other>.yaml
```

### Run the Tier 2 pipeline

`pattern_extract` instead of `schema_extract`, same shared downstream
states, its own workflow YAML:

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-pattern-tier.yaml
```

Or target a specific already-seeded Tier 2 hypothesis (`tier=2` in
`hypotheses`, `property_conditions` non-null) the same way as Tier 1:

```bash
uv run --frozen python -m harness.engine.runner harness/workflows/storage-pattern-tier.yaml \
  --start-state rule_compile --context '{"target_hypothesis_id": <id>}'
```

### Regression-check the whole rule set for real

```bash
uv run --frozen python -m harness.tools.regression_check
```

Parallel (`ThreadPoolExecutor`, I/O-bound on `az`/`conftest` subprocess
calls) and safe to parallelize because it's read-only against the
journal and each check_id's work touches only its own files -- see
`harness/tools/regression_check.py`'s module docstring. Confirmed
against Storage's 52 rules: 10m34s sequential (`--workers 1`) vs 2m40s
with the default 8 workers, both `ALL PASSED`.

Reads each fixture's `variants_json` so it covers Tier 1 (2 variants)
and Tier 2 (N variants) rules in the same loop -- falls back to the
original vulnerable/safe pair for any older row with `variants_json IS
NULL`. Use `--workers 1` to reproduce strictly-sequential behavior, and
`--policy-dir`/`--db` to point at a different resource type's rules or
a scratch journal. `--policy-dir` also filters *which* rules are
checked (by `rule_path` prefix), not just where `conftest` loads
policies from -- necessary once multiple resource types can share one
journal across git worktrees (see "Sharing one journal across
worktrees" below): a worktree only has the fixture/rule files for its
own resource type on disk, so checking every rule in the journal
regardless of `--policy-dir` would try to compile fixtures that don't
exist there and report them as false failures.

## Known gaps (not actioned, flagged deliberately)

- **No automated regression gate.** Adding a new rule to a shared
  `rules/<...>/` directory doesn't automatically re-check all
  previously-validated fixtures in that directory. The per-check Rego
  namespace convention (`checks.<check_id>`) prevents the specific
  cross-contamination bug already found and fixed, but it isn't a
  general safety net against a differently-shaped bug. Worth a real CI
  step.
- **`rule_compile.md`'s `==`-vs-`!=` guidance is prompt-level, not
  enforced.** Confirmed inconsistently followed even with the guidance
  present and a near-identical hypothesis getting it right moments
  earlier in the same batch run (`AZ-STOR-041`). See
  `docs/patterns/rego-rule-authoring.md`.
- **Tier 2's dedup guard is weaker than Tier 1's `schema_coverage`
  ledger.** `apply_pattern_hypotheses` only skips an exact
  property-path-set match per resource_type -- there's no equivalent of
  "have we fully covered the space" since the combinatorial space isn't
  enumerable (see the plan's open questions in
  `docs/plans/active/2026-07-02-tier-2-pattern-checks.md`).
- **Tier 2 is only wired up for Storage.** A second resource type wants
  its own `pattern_extract.md` and `<slug>-pattern-tier.yaml`; not
  automated by `bootstrap_resource_type.py` yet.
- **Tier 3 doesn't exist**, as covered above.
