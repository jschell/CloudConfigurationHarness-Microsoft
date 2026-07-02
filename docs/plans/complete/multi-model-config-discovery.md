# Multi-Model Cloud Configuration Discovery Harness

## Goal

Build an orchestration harness that uses Claude (via Claude Code, Anthropic
endpoint) and GLM (via Claude Code, Z.ai Anthropic-compatible endpoint) as
interchangeable roles inside a deterministic, journaled workflow that
discovers Azure configuration attack-path hypotheses from published
schema/docs (not live subscriptions), compiles them into fixture-validated,
version-controlled rules, and executes those rules repeatably and
deterministically without further LLM involvement.

## Architecture

Three layers, strictly separated:

1. **Journal (source of truth)** — SQLite database. Every workflow state
   reads from and writes to this. No state lives only in an LLM context
   window.
2. **Workflow engine (orchestration)** — a finite-state machine defined in
   YAML, executed by a lightweight runner. Each state declares: which role
   runs it (`orchestrator` or `executor`), which model backs that role,
   what it reads from the journal, what it must write back.
3. **Deterministic adapters (verification)** — standalone, model-free tools
   invoked as subprocesses: `az bicep build`, `az deployment group
   validate`, OPA/`conftest` for Rego evaluation. These are the only
   components allowed to produce a pass/fail verdict on a fixture.

Model access: both Claude and GLM are driven through the same Claude Code
CLI, invoked headless (`claude -p ...`), differing only in which API
endpoint the process environment points at (`ANTHROPIC_BASE_URL` +
`ANTHROPIC_API_KEY` swapped per invocation). No LiteLLM gateway in this
phase — that is an explicit YAGNI deferral until a third,
non-Anthropic-protocol model is needed.

Data flow for one atomic-check cycle:

```
schema_extract (LLM) -> journal:hypotheses
  -> rule_compile (LLM) -> journal:rules (status=draft)
  -> fixture_generate (LLM) -> journal:fixtures
  -> fixture_validate (deterministic adapter, no LLM) -> journal:runs
  -> gate: pass -> journal:rules (status=validated) / fail -> back to rule_compile
```

## Tech Stack

* SQLite (journal)
* Python for the workflow runner
* YAML for FSM workflow definitions
* Claude Code CLI, headless mode (`-p`, `--output-format json`), invoked as
  subprocess by the workflow runner
* Azure CLI (`az bicep`, `az deployment group validate`) as the schema/ARM
  deterministic adapter
* Open Policy Agent (`opa` / `conftest`) as the Rego deterministic adapter
* Git for rule/fixture version control (rules and fixtures are files in the
  repo, not only journal rows — journal tracks provenance and run history,
  git tracks content history)

## Repository Layout

```
cloud-config-harness/
  docs/plans/                          # this file and future plans
  harness/
    journal/
      schema.sql                       # DDL
      db.py                            # connection/migration helper
    engine/
      runner.py                        # FSM executor
      roles.yaml                       # model-to-role config
      compare_runs.py                  # A/B comparison reporting
    adapters/
      bicep_validate.py                # wraps az bicep/deployment validate
      rego_validate.py                 # wraps opa/conftest
    workflows/
      storage-atomic-tier.yaml         # first FSM definition
      prompts/                         # prompt templates per state
  rules/
    azure/storage/
      AZ-STOR-001.rego
  fixtures/
    azure/storage/
      AZ-STOR-001/
        vulnerable.bicep
        safe.bicep
        expected.json
  sources/
    azure/storage/
      swagger-refs.md
```

See the task list this plan was derived from for the full Task 1-7
breakdown and verification steps. Non-goals: no live Azure subscription
access, no LiteLLM gateway, no additional resource types beyond Storage, no
Tier 2/3 (pattern/chained) workflows in this phase.
