# Pattern: structured, non-overlapping, completable schema discovery

## The problem this solves

Before this pattern, `schema_extract` worked from a hand-curated markdown
excerpt of a resource type's swagger spec and used LLM judgment, advised
by a "don't repeat what's already in `hypotheses`" instruction, to decide
what to propose. That left three real gaps:

1. **Not structured** -- whatever the curator (human or model) happened
   to transcribe into the excerpt was the ceiling of what could ever be
   discovered. Nothing forced consideration of every property on the
   resource.
2. **Overlap not enforced** -- "avoid duplicates" was advisory, checked
   nowhere in code. A model re-proposing something already decided (or
   hallucinating a near-duplicate) would just get inserted.
3. **No completion signal** -- nothing tracked "how much of this resource
   have we actually considered." A run just proposed whatever it proposed
   that pass; there was no way to know if that was 8 of 12 relevant
   properties or 8 of 166.

This pattern replaces all three with code, not model judgment:
deterministic enumeration, a database-enforced dedup guard, and an
explicit completeness ledger.

## The pieces

| Piece | What it does | File |
|---|---|---|
| Enumerator | Deterministically walks a swagger definition (resolving `$ref`s) and lists every leaf property, no LLM involved | `harness/tools/enumerate_schema_properties.py` |
| Coverage ledger | One row per `(resource_type, property_path)`, ever, recording relevant-or-not + rationale + which hypothesis it became (if any) | `schema_coverage` table, `harness/journal/schema.sql` |
| Batch classifier | Feeds the model only the properties NOT yet in the ledger, in small batches, and applies results through a dedup-guarded insert | `harness/tools/run_schema_coverage.py` |
| Completion check | Diffs the enumerated list against the ledger; `complete: True` iff nothing remains | `harness/tools/coverage_status.py` |
| Shared insertion logic | The actual dedup-guarded write path, used by both the batch classifier and the FSM's `schema_extract` state | `harness.engine.handlers.apply_schema_classifications` |

## How it answers the three original questions

**Structured generation:** `enumerate_schema_properties.py` produces a
complete, code-generated property list from the real swagger JSON (not a
curated excerpt) -- for Storage, 166 properties, resolving nested `$ref`s
like `networkAcls` -> `NetworkRuleSet` -> `defaultAction` into dotted
paths. This is committed to the repo (`sources/<provider>/<resource>/
<name>.enumerated.json`) with a `source_note` recording exactly which
swagger commit it came from, so it's reproducible.

**No overlap:** `schema_coverage` has a `UNIQUE (resource_type,
property_path)` constraint, and `apply_schema_classifications` checks it
*before* inserting anything -- in code, not by asking the model nicely.
The batch classifier goes further and never even shows the model a
property already in the ledger, so it can't re-propose one by
construction, not just by instruction.

**Knowing when done:** `coverage_status.py` is a direct diff: enumerated
property count vs. distinct `schema_coverage` rows for that
`resource_type`. `complete: True` means every property has been
classified one way or the other -- not "we ran it a few times and stopped
noticing new ones."

## Applying this to a new resource type/component

1. Fetch the resource's swagger definition (pinned to a commit, same as
   the existing `sources/azure/storage/swagger-refs.md` convention) and
   enumerate it:

   ```
   uv run python -m harness.tools.enumerate_schema_properties \
       <path-to-swagger.json> <RootDefinitionName> \
       --source-note "Azure/azure-rest-api-specs@<sha> <path>" \
       --out sources/<provider>/<resource>/<name>.enumerated.json
   ```

2. Add a `schema.sql`-compatible narrative/policy-catalog file for the
   new resource, same shape as `sources/azure/storage/swagger-refs.md`
   (existing built-in policy coverage, for grounding
   `existing_policy_ref`).

3. Run the batch classifier against the real, persistent journal (no
   `--db` override):

   ```
   uv run python -m harness.tools.run_schema_coverage \
       sources/<provider>/<resource>/<name>.enumerated.json \
       "<Microsoft.Provider/resourceType>" \
       --extra-file sources/<provider>/<resource>/<narrative>.md \
       --batch-size 10
   ```

4. Confirm completion:

   ```
   uv run python -m harness.tools.coverage_status \
       sources/<provider>/<resource>/<name>.enumerated.json \
       "<Microsoft.Provider/resourceType>"
   ```

5. From here on, the normal FSM (`rule_compile` -> `fixture_generate` ->
   `fixture_validate` -> `gate`) picks up each hypothesis the classifier
   found, exactly as it already does for Storage.

If the source schema changes later (new API version), re-run step 1 and
step 3 again -- previously classified properties are skipped (dedup
guard), so this is a cheap incremental re-check, not a redo. If a
property is later removed from the schema, `coverage_status.py` reports
it as "stale" (in the ledger but not the current enumeration) rather than
silently dropping it, so removed history is still visible.

## Lessons from actually running this (Storage, 2026-07-02)

- **Batch, don't send everything in one call.** A single call covering
  all ~158 remaining properties for Storage hit a transient Anthropic
  `529 overloaded` and separately a `subprocess` timeout in the same
  session. Batches of 10 are cheap to retry individually and never lose
  already-committed progress -- each batch's `schema_coverage` insert
  commits before the next batch starts.
- **Large prompts break Windows `subprocess.run(list_form)`.** Passing
  the full rendered prompt as a CLI argument to `claude -p <prompt>` hit
  `WinError 206: filename or extension too long` once the enumerated
  property list pushed the prompt past Windows' command-line length
  limit. Fixed in `runner._invoke_claude` by piping the prompt via stdin
  (`subprocess.run(..., input=prompt)`) instead of passing it as an
  argv element -- this also removes any argument-length ceiling
  entirely, on any platform.
- **GLM completed this task faster and more reliably than Claude** in
  this session: Claude's orchestrator role hit sustained `529`s when the
  driver was pointed at it; re-running the identical batch job with
  `--role executor_glm` completed all 16 batches (166/166 properties)
  with zero retries needed. Worth defaulting structured-discovery sweeps
  like this to `executor_glm` and reserving Claude for cases that
  specifically need it, at least until Anthropic's capacity issues (seen
  live during this session) are less of a factor.
- **Backfill before switching a resource type onto this pattern.** If
  hypotheses already exist for a resource type from before
  `schema_coverage` existed (or from before this pattern was adopted),
  backfill `schema_coverage` rows for them first -- otherwise the batch
  classifier doesn't know they're already covered and will re-derive
  (and duplicate) them.
