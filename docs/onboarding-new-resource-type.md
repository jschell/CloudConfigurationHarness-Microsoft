# Onboarding a new Azure resource type

This is the generalized version of how Storage was onboarded (see
`docs/status/2026-07-01-status.md` and `docs/status/2026-07-02-status.md`
for that history). As of this doc, `harness/engine/handlers.py` is
generic across resource types via each workflow's `resource_config`
block -- **nothing in `handlers.py` needs to change** to onboard a new
one; you only add new files.

## What's automated vs. what isn't

`harness/tools/bootstrap_resource_type.py` automates:

1. Resolving a swagger ref to an exact commit SHA and enumerating every
   property on the given root definition (no LLM, deterministic,
   reproducible -- see `docs/patterns/schema-coverage-discovery.md`).
2. Best-effort discovery of existing Azure Policy built-ins referencing
   the resource type, via GitHub code search.
3. Scaffolding the workflow YAML and the resource-specific
   `schema_extract.md` prompt from templates.

What it does **not** automate, and why:

- **Picking the swagger file/commit/root-definition in the first
  place.** This needs a human (or an LLM doing real research) to find
  the right file in `Azure/azure-rest-api-specs` and the right
  `...Properties` definition name -- there's no reliable way to guess
  this from just a resource type string.
- **Judging which discovered policy built-ins are actually relevant.**
  Code search is best-effort and known to return false positives (a
  resource type string appearing in an unrelated policy's condition) and
  false negatives (indexing lag, formatting differences). The generated
  `*-policy-refs.md` is a starting point for human review, not a
  finished document.
- **Everything past scaffolding.** `schema_extract`, `rule_compile`,
  `fixture_generate` are still real LLM calls against the real journal,
  run the same way as for Storage -- see `docs/operating-tiers.md`.

## Step by step

### 1. Find the swagger definition

Browse `Azure/azure-rest-api-specs` for the resource's Resource Manager
swagger (usually `specification/<service>/resource-manager/<provider>/.../stable/<version>/<file>.json`)
and find the `...Properties` definition name for the resource
(`grep '"Properties"' <file>.json` or just read it). This is the one
step this whole process most depends on getting right -- everything
downstream reads from this file.

### 2. Run the bootstrap script

Real example, run for real while building this (kept in the repo as a
concrete reference -- `sources/azure/keyvault/`,
`harness/workflows/keyvault-atomic-tier.yaml`):

```bash
uv run --frozen python -m harness.tools.bootstrap_resource_type \
  --swagger-repo Azure/azure-rest-api-specs \
  --swagger-ref main \
  --swagger-path specification/keyvault/resource-manager/Microsoft.KeyVault/KeyVault/stable/2023-07-01/keyvault.json \
  --root-definition VaultProperties \
  --resource-type Microsoft.KeyVault/vaults \
  --slug keyvault \
  --provider-dir azure/keyvault \
  --check-id-prefix AZ-KV
```

This writes:

- `sources/<provider-dir>/<slug>-properties.enumerated.json` -- the
  exhaustive property list.
- `sources/<provider-dir>/<slug>-policy-refs.md` -- best-effort policy
  catalog (needs review, see below).
- `harness/workflows/<slug>-atomic-tier.yaml` -- the FSM, with
  `resource_config` filled in.
- `harness/workflows/prompts/<slug>/schema_extract.md` -- the
  resource-specific discovery prompt. `rule_compile.md`/
  `fixture_generate.md` are shared and reused automatically; nothing to
  generate for those.

Requires the `gh` CLI, authenticated (used for both the swagger commit
resolution and the policy code search).

### 3. Review the generated policy-refs file by hand

Open `sources/<provider-dir>/<slug>-policy-refs.md`. Delete hits that are
clearly false positives (the resource type string appearing in an
unrelated policy). It's fine to leave it imperfect -- `schema_extract`
uses it for grounding `existing_policy_ref`, not as ground truth; a
missing or slightly-off entry there doesn't block discovery, it just
means that one hypothesis won't have a built-in policy citation.

### 4. Sweep to full property coverage

```bash
uv run --frozen python -m harness.tools.run_schema_coverage \
  sources/<provider-dir>/<slug>-properties.enumerated.json \
  "<resource type>" \
  --extra-file sources/<provider-dir>/<slug>-policy-refs.md \
  --batch-size 10
```

Confirm completion:

```bash
uv run --frozen python -m harness.tools.coverage_status \
  sources/<provider-dir>/<slug>-properties.enumerated.json \
  "<resource type>"
```

`complete: True` means every property has been classified relevant or
not. See `docs/patterns/schema-coverage-discovery.md` for what "batch
size" is protecting against (large single calls hit real transient
failures during Storage's onboarding) and why GLM (`--role executor_glm`,
already the tool's default) is the recommended default model for this
step specifically.

### 5. Compile every discovered hypothesis into a validated rule

```bash
uv run --frozen python -m harness.tools.run_hypothesis_buildout \
  --workflow harness/workflows/<slug>-atomic-tier.yaml
```

This only processes hypotheses tagged with this workflow's own
`resource_config.resource_type` -- safe to run for multiple resource
types against the same journal without them interfering with each
other's check_id numbering (see
`docs/patterns/deterministic-check-id-assignment.md`).

### 6. Regression-check the new rule set for real

Same pattern as `docs/operating-tiers.md`'s regression-check snippet, but
pointed at the new `rules_dir`/`fixtures_dir`.

KeyVault was carried all the way through steps 3-6 for real -- not just
bootstrapped -- proving this process (and `handlers.py`'s
resource-type-generic design) holds up on a second resource type, not
just Storage. Every discovered Tier 1 hypothesis compiled to a validated
rule on the first pass, including the array-typed `accessPolicies[]`/
`networkAcls.ipRules[]` properties flagged as an open question during
bootstrap -- the model produced the correct `some x in array; x == value`
Rego idiom on its own, with no example of it in `rule_compile.md`, so no
prompt-template change was needed.

## Before you start: read these

- `docs/patterns/schema-coverage-discovery.md` -- why enumeration is
  deterministic and classification is batched.
- `docs/patterns/rego-rule-authoring.md` -- the `==`-vs-`!=` pitfall;
  applies to every resource type's rules, not just Storage's.
- `docs/patterns/deterministic-check-id-assignment.md` -- why check_id
  is handler-assigned, not model-assigned.
- `docs/operating-tiers.md`'s **"A real hazard: `--db` does NOT isolate
  file writes"** section, if you're going to test any of this against a
  scratch database before running it for real.
