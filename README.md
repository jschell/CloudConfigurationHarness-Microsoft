# Multi-Model Cloud Configuration Discovery Harness

An orchestration harness that uses Claude and GLM (both driven through the
Claude Code CLI, differing only by which API endpoint they point at) as
interchangeable roles inside a deterministic, journaled workflow that
discovers Azure configuration attack-path hypotheses from published
schema/docs, compiles them into fixture-validated, version-controlled
Rego rules, and executes those rules repeatably without further LLM
involvement.

Full design: [docs/plans/multi-model-config-discovery.md](docs/plans/multi-model-config-discovery.md).
Current state and open gaps: the most recent file in [docs/status/](docs/status/)
(latest: [docs/status/2026-07-02-status.md](docs/status/2026-07-02-status.md)).

## Architecture, briefly

Three layers, strictly separated:

1. **Journal (source of truth)** -- SQLite (`harness/journal/harness.db`,
   local, gitignored). Every workflow state reads from and writes to it.
   Schema in `harness/journal/schema.sql`, applied idempotently.
2. **Workflow engine** -- a finite-state machine defined in YAML
   (`harness/workflows/*.yaml`), executed by `harness/engine/runner.py`.
   Each state declares which role runs it and which journal tables it
   reads/writes.
3. **Deterministic adapters** -- `az bicep build` and `opa`/`conftest`,
   wrapped in `harness/adapters/`. These are the only components allowed
   to produce a pass/fail verdict on a fixture; no LLM is involved in
   verification.

Rules and fixtures are files in the repo (`rules/`, `fixtures/`), tracked
by git like any other source. The journal tracks provenance and run
history (which model produced what, when, and whether it validated) --
see `rule_history`/`fixture_history` in the schema.

## Repository layout

```
docs/
  plans/            the original design doc
  status/            dated session summaries -- what's done, what's stubbed, what's next
  patterns/          reusable lessons (see below) -- read before touching rule authoring or discovery logic
  task-runs/         one-off A/B comparison reports
harness/
  journal/           schema.sql + db.py (SQLite connection/migration)
  engine/            runner.py (FSM executor), handlers.py (state logic), roles.yaml, compare_runs.py, preflight.py
  adapters/          bicep_validate.py, rego_validate.py
  tools/             standalone scripts: schema enumeration, batch classification, batch rule buildout, coverage reporting
  workflows/         *.yaml FSM definitions + workflows/prompts/*.md (per-state LLM prompts)
sources/
  azure/storage/     pinned swagger excerpts + the enumerated property list for Storage
rules/
  azure/storage/     validated Rego checks (AZ-STOR-NNN.rego)
fixtures/
  azure/storage/     vulnerable.bicep/safe.bicep pairs per check
```

## Quick start

```bash
# one-time environment setup
uv sync
export UV_LINK_MODE=copy   # only needed if the repo lives on a filesystem without hardlink support (e.g. OneDrive)

# confirm required tools are present before running anything for real
uv run --frozen python -m harness.engine.preflight harness/workflows/storage-atomic-tier.yaml

# run the full pipeline (discovery -> compile -> validate) against the real journal
uv run --frozen python -m harness.engine.runner harness/workflows/storage-atomic-tier.yaml
```

See [docs/operating-tiers.md](docs/operating-tiers.md) for the full
command reference (targeting a specific hypothesis, A/B comparing
models, batch-classifying an entire resource's properties, resuming an
interrupted run) and [docs/onboarding-new-resource-type.md](docs/onboarding-new-resource-type.md)
for pulling in a new Azure resource type beyond Storage.

## Read these before making changes

Three real bugs shipped and were caught only by actually running this at
scale, not by review. Each is written up with the *why*, not just the
fix, specifically so they don't get silently reintroduced:

- [docs/patterns/schema-coverage-discovery.md](docs/patterns/schema-coverage-discovery.md)
  -- deterministic property enumeration + batched classification +
  completeness ledger, instead of curated doc excerpts and LLM judgment
  alone.
- [docs/patterns/rego-rule-authoring.md](docs/patterns/rego-rule-authoring.md)
  -- prefer denying on the negation of a safe value over matching one
  named risky value, whenever a property has more than two states.
- [docs/patterns/deterministic-check-id-assignment.md](docs/patterns/deterministic-check-id-assignment.md)
  -- never let a stateless model call invent an identifier whose
  uniqueness matters; assign it in code.

## Status

All 41 Storage-account Tier-1 (atomic) checks are compiled, validated,
and committed -- 166/166 (100%) property coverage for
`Microsoft.Storage/storageAccounts`. See
[docs/status/2026-07-02-status.md](docs/status/2026-07-02-status.md) for
detail, and [docs/operating-tiers.md](docs/operating-tiers.md) for what
Tier 2/3 (combination/chained checks) would need, which isn't built yet.
