# Feature: KeyVault Tier 1 (atomic) checks

## Goal

Take `Microsoft.KeyVault/vaults` from "bootstrapped but undiscovered"
to "a real, validated set of Tier 1 checks" -- the second resource
type onboarded after Storage, proving `harness/engine/handlers.py`'s
generic-across-resource-types design actually holds up on something
that isn't Storage.

## Architecture

Nothing new to design -- `docs/onboarding-new-resource-type.md` already
describes the whole process, and Storage already proved
`rule_compile`/`fixture_generate`/`fixture_validate`/`gate` need zero
per-resource-type code changes. KeyVault's bootstrap step (step 1-2 of
that doc) is **already done**, real, and committed:

- `sources/azure/keyvault/keyvault-properties.enumerated.json` -- 34
  properties, enumerated from `VaultProperties` in
  `Azure/azure-rest-api-specs@a5f34026d` (pinned commit, see the file's
  `source_note`).
- `sources/azure/keyvault/keyvault-policy-refs.md` -- best-effort
  policy catalog from GitHub code search. **Not yet reviewed by hand**
  (onboarding doc step 3) -- it currently has clear false positives:
  several `Deploy-GitOps-*-Kubernetes-*` and
  `RestrictToDisconnectedServices_Audit` entries whose `policyRule.if`
  references `Microsoft.Kubernetes/connectedClusters` /
  `Microsoft.ContainerService/managedClusters` or a generic
  parameterized type list, not `Microsoft.KeyVault/vaults` at all --
  the resource type string only appears in the policy's *title*
  ("...to Kubernetes cluster...with...secrets in KeyVault"), which is
  exactly the false-positive failure mode the onboarding doc warns
  about. This plan's Task 1 is that review.
- `harness/workflows/keyvault-atomic-tier.yaml` -- FSM, already wired
  to the shared states.
- `harness/workflows/prompts/keyvault/schema_extract.md` -- fully
  generated from the template, no placeholders left.

So this plan starts at onboarding doc step 3 (review policy-refs),
runs steps 4-6 for real (schema coverage sweep, hypothesis buildout,
regression check), and stops there -- Tier 2 for KeyVault is
explicitly out of scope (see Open Questions).

**One real difference from Storage worth flagging up front, not
solving speculatively:** KeyVault's enumerated properties include
array-typed paths that Storage's did not need to handle in
`rule_compile.md`'s existing guidance -- e.g.
`properties.accessPolicies[].objectId`,
`properties.networkAcls.ipRules[]`. The shared `rule_compile.md`'s
Rego example (`resource.properties.<path minus "properties."> ==
"<value>"`) is written for scalar properties; a hypothesis whose
`property_path` contains a bare array index (`[]`) will need a
`some x in resource.properties.accessPolicies; x.objectId == ...`-style
rule instead, and the current prompt doesn't say so. Task 3 below
surfaces whether this actually blocks a real hypothesis (some/most of
KeyVault's security-relevant properties, like `networkAcls.defaultAction`
and `publicNetworkAccess`, are scalar and unaffected) before deciding
whether `rule_compile.md` needs new guidance -- don't add
array-handling instructions to a shared prompt template speculatively
if nothing in KeyVault's actual hypothesis set needs it.

## Tech Stack

Same as the rest of the harness: Python 3.11, SQLite, YAML workflow
definitions, `az bicep build` + `conftest` as the deterministic
verifier, GLM (`executor_glm`, the harness default for
`rule_compile`/`fixture_generate`) and Claude (`orchestrator`, the
default for `schema_extract`/`run_schema_coverage`). **No automated
test suite exists in this repo** -- every task here is a real
end-to-end run against the live journal and real `az`/`conftest`/model
APIs, matching how Storage's onboarding and both Tier 2 plans were
actually verified.

**Environment reminders** (see `docs/operating-tiers.md`): export
`UV_LINK_MODE=copy`; prepend
`C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin` to `PATH` if `az`
reports MISS; **never run `rule_compile`/`fixture_generate` against a
scratch `--db`** without first seeding it with dummy rows for every
real check_id already in use (this plan operates entirely against the
real journal, `harness/journal/harness.db`, so this shouldn't come up,
but don't introduce a scratch `--db` run without rereading that
warning first).

## Tasks

### Task 1: Review and prune `keyvault-policy-refs.md` by hand

**File:** `sources/azure/keyvault/keyvault-policy-refs.md`

#### Steps:

1. Confirm the false positives are real by checking each entry's
   `policyRule.if` for whether it actually names
   `Microsoft.KeyVault/vaults` (case-insensitive; the file has both
   `Microsoft.KeyVault/vaults` and `microsoft.keyvault/vaults`
   spellings from different policy authors) as a `field: type` /
   `equals` condition, versus only appearing in the entry's title:
   ```bash
   grep -n "^- \`" sources/azure/keyvault/keyvault-policy-refs.md
   ```
   For each line, check the very next line's `policyRule.if` blob for
   `"field": "type", "equals": "Microsoft.KeyVault/vaults"` (or the
   lowercase spelling) versus `Microsoft.Kubernetes/connectedClusters`,
   `Microsoft.ContainerService/managedClusters`, or a generic
   `resourceTypeList`/`listOfResourceTypesSupportedIn*` parameter.

2. Delete every entry whose `policyRule.if` does not reference
   `Microsoft.KeyVault/vaults`/`microsoft.keyvault/vaults` as an actual
   type condition. Based on the current file, that's the GitOps/Flux2
   Kubernetes entries (both the standard and "Azure Government"
   variants) and the `RestrictToDisconnectedServices_Audit` (Azure
   Local) entry. Use judgment on
   `DiagnosticSettingsExistsAudit_Audit.json` too -- its `policyRule.if`
   is a generic `resourceTypeList` parameter, not KeyVault-specific,
   which is the same false-positive shape as the others even though
   its title doesn't mention Kubernetes.

3. Leave the genuinely KeyVault-specific entries even if they look
   redundant (e.g. the "Azure Government" and non-Government versions
   of the same policy, or the duplicate `PublicNetworkAccess_Audit.json`
   appearing under two different policy category folders) --
   `schema_extract.md` only uses this file for grounding
   `existing_policy_ref`, redundant-but-accurate entries don't hurt,
   only wrong ones do.

4. Verify the remaining count and spot-check a few:
   ```bash
   grep -c "^- \`" sources/azure/keyvault/keyvault-policy-refs.md
   ```
   Expect meaningfully fewer than the original count (the file started
   with the Kubernetes/GitOps and Azure Local entries mixed in).

5. Commit: `"Prune false-positive policy refs from keyvault-policy-refs.md"`

### Task 2: Sweep KeyVault's 34 properties to full schema coverage

**No new files** -- runs the existing, resource-type-generic
`harness/tools/run_schema_coverage.py` and
`harness/tools/coverage_status.py` against KeyVault's enumerated list.

#### Steps:

1. Confirm the starting state (nothing classified yet):
   ```bash
   uv run --frozen python -m harness.tools.coverage_status \
     sources/azure/keyvault/keyvault-properties.enumerated.json \
     "Microsoft.KeyVault/vaults"
   ```
   Expect `0/34` classified, `complete: False`.

2. Run the sweep, in batches (see
   `docs/patterns/schema-coverage-discovery.md` for why batching
   matters -- a single 34-property call is smaller than Storage's ~72
   and might succeed in one shot, but batching is still the safer
   default given the same transient-failure history that motivated
   this tool):
   ```bash
   uv run --frozen python -m harness.tools.run_schema_coverage \
     sources/azure/keyvault/keyvault-properties.enumerated.json \
     "Microsoft.KeyVault/vaults" \
     --extra-file sources/azure/keyvault/keyvault-policy-refs.md \
     --batch-size 10
   ```
   Expect it to run to `done: 34/34 properties classified for
   Microsoft.KeyVault/vaults`, retrying individual batches on
   transient failures per the tool's own retry loop.

3. Confirm completion:
   ```bash
   uv run --frozen python -m harness.tools.coverage_status \
     sources/azure/keyvault/keyvault-properties.enumerated.json \
     "Microsoft.KeyVault/vaults"
   ```
   Expect `complete: True`.

4. Sanity-check the relevant/not-relevant split and read a few
   rationales for obviously-important properties (don't just trust the
   count -- verify the model actually flagged the properties you'd
   expect a security engineer to flag):
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   rows = conn.execute(\"SELECT property_path, relevant, rationale FROM schema_coverage WHERE resource_type='Microsoft.KeyVault/vaults' ORDER BY property_path\").fetchall()
   relevant = [r for r in rows if r['relevant']]
   print(f'{len(relevant)}/{len(rows)} marked relevant')
   for r in relevant:
       print(' -', r['property_path'])
   "
   ```
   Expect properties like `properties.networkAcls.defaultAction`,
   `properties.publicNetworkAccess`, `properties.enableSoftDelete`,
   `properties.enablePurgeProtection`, `properties.enableRbacAuthorization`
   (all directly named in the policy-refs catalog from Task 1) to
   appear in the relevant list. If an obviously-important property
   from that list is missing, that's a real finding -- don't silently
   proceed to Task 3 with an incomplete relevant-set; investigate
   whether `schema_extract.md`'s guidance needs sharpening the same way
   Storage's did during its own onboarding (see
   `docs/patterns/schema-coverage-discovery.md`).

5. No commit needed for this task by itself -- `schema_coverage`/
   `hypotheses` rows live only in the gitignored journal
   (`harness/journal/harness.db`), nothing on disk to commit yet.

### Task 3: Compile every discovered hypothesis into a validated rule

**No new files** -- runs `harness/tools/run_hypothesis_buildout.py`.

#### Steps:

1. Check whether `run_hypothesis_buildout.py` has picked up the
   tier-filter fix from `docs/plans/queue/2026-07-02-tier-2-storage-buildout.md`
   (that plan may or may not have executed yet by the time this one
   does -- they're independent and queued separately):
   ```bash
   grep -n "def remaining_hypothesis_ids" -A 3 harness/tools/run_hypothesis_buildout.py
   ```
   - If its signature is `remaining_hypothesis_ids(conn, resource_type: str, tier: int)`,
     the tool now requires `workflow["resource_config"]["tier"]` to
     exist. Add `tier: 1` to `harness/workflows/keyvault-atomic-tier.yaml`'s
     `resource_config:` block (matching the key ordering already used
     in `storage-atomic-tier.yaml` if that file has been updated the
     same way) before proceeding.
   - If its signature still only takes `(conn, resource_type: str)`,
     no change needed -- KeyVault has no Tier 2 workflow yet, so the
     collision risk that fix addresses doesn't apply here regardless.

2. Confirm what's pending:
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   n = conn.execute(\"SELECT COUNT(*) c FROM hypotheses WHERE resource_type='Microsoft.KeyVault/vaults'\").fetchone()['c']
   print(n, 'hypotheses for KeyVault, 0 compiled so far')
   "
   ```

3. Run the buildout:
   ```bash
   uv run --frozen python -m harness.tools.run_hypothesis_buildout \
     --workflow harness/workflows/keyvault-atomic-tier.yaml
   ```
   Expect one `=== hypothesis <id> ===` block per KeyVault hypothesis,
   each ending `AZ-KV-NNN: validated` or `AZ-KV-NNN: rejected` (both
   legitimate outcomes -- see the tool's own docstring). This is where
   the array-typed-property question flagged in Architecture becomes
   concrete: if a hypothesis whose `property_path` contains `[]` gets
   `rejected` after 3 attempts specifically because the generated Rego
   can't correctly index into an array (check the rejected check_id's
   `rule_history` / `last_failure_reason` for a pattern like "expected
   fail, got pass" on the vulnerable fixture), that confirms the gap is
   real and worth fixing in `harness/workflows/prompts/rule_compile.md`
   (a follow-up task, not silently retried past this plan's scope) --
   if every array-typed hypothesis instead validates fine (GLM may
   already know the correct Rego idiom without being told), no action
   needed.

4. Query final status for every KeyVault rule:
   ```bash
   uv run --frozen python -c "
   from harness.journal.db import connect
   conn = connect('harness/journal/harness.db')
   for r in conn.execute(\"\"\"
       SELECT r.check_id, r.status, h.property_path
       FROM rules r JOIN hypotheses h ON r.hypothesis_id = h.id
       WHERE h.resource_type = 'Microsoft.KeyVault/vaults' ORDER BY r.check_id
   \"\"\"):
       print(dict(r))
   "
   ```
   Record `validated` vs `rejected` counts and which (if any)
   `rejected` checks involve array-typed properties, for the Task 5
   writeup.

5. Commit whatever landed on disk:
   ```bash
   git add rules/azure/keyvault fixtures/azure/keyvault
   git status --short   # confirm nothing unexpected is staged
   git commit -m "Build out KeyVault Tier 1 checks via run_hypothesis_buildout"
   ```

### Task 4: Regression-check the KeyVault rule set for real

**No new files** -- reuses whichever regression-check tooling exists
at execution time.

#### Steps:

1. Check whether `harness/tools/regression_check.py` exists yet (built
   by `docs/plans/queue/2026-07-02-tier-2-storage-buildout.md`'s Task
   4 -- may or may not have landed before this plan runs):
   ```bash
   ls harness/tools/regression_check.py 2>&1
   ```

2. **If it exists**, use it directly (it already parameterizes
   `--policy-dir`/`--db`, no code change needed for a new resource
   type):
   ```bash
   uv run --frozen python -m harness.tools.regression_check --policy-dir rules/azure/keyvault
   ```
   Note this only regression-checks the rules under that one
   `--policy-dir` -- it doesn't currently filter the `rules`/`fixtures`
   join by resource type, so it'll report on every `check_id` whose
   `rule_path` happens to resolve under `rules/azure/keyvault`, which
   for a clean journal is exactly (and only) the KeyVault rules. If
   `regression_check.py` was extended before this plan runs and that
   assumption no longer holds, adjust this step accordingly rather than
   trusting this stale note.

3. **If it doesn't exist yet**, fall back to the same ad-hoc pattern
   used throughout this project's history, pointed at KeyVault's dirs:
   ```bash
   uv run --frozen python -c "
   import json
   from harness.journal.db import connect
   from harness.adapters import bicep_validate, rego_validate
   from pathlib import Path

   conn = connect('harness/journal/harness.db')
   policy_dir = Path('rules/azure/keyvault')
   all_ok = True
   rows = conn.execute(\"\"\"
       SELECT r.check_id FROM rules r JOIN hypotheses h ON r.hypothesis_id = h.id
       WHERE h.resource_type = 'Microsoft.KeyVault/vaults' ORDER BY r.check_id
   \"\"\").fetchall()
   print(f'checking {len(rows)} rules')
   for r in rows:
       check_id = r['check_id']
       fixture_row = conn.execute('SELECT variants_json FROM fixtures WHERE check_id=?', (check_id,)).fetchone()
       fixture_dir = Path(f'fixtures/azure/keyvault/{check_id}')
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

4. Expect `ALL PASSED`. Also confirm no cross-contamination with
   Storage's rules sharing the *journal* (they don't share a `rules/`
   directory, so conftest's per-directory `--policy` load can't mix
   them, but it's worth a rerun of Storage's own regression check too
   as a belt-and-suspenders check that onboarding a second resource
   type didn't disturb the first):
   ```bash
   uv run --frozen python -m harness.tools.regression_check --policy-dir rules/azure/storage
   # or the Storage-pointed version of the ad-hoc snippet if regression_check.py doesn't exist yet
   ```
   Expect `ALL PASSED` for Storage too, unchanged from before this
   plan started.

5. If anything fails, diagnose using the same process as prior plans
   (namespace contamination first, per
   `docs/patterns/deterministic-check-id-assignment.md`, then the
   `==`-vs-`!=` guidance in `docs/patterns/rego-rule-authoring.md`).

6. No commit -- this task is pure verification.

### Task 5: Update docs with KeyVault's real results

**Files:** `docs/onboarding-new-resource-type.md`,
`docs/patterns/README.md` (only if warranted)

#### Steps:

1. `docs/onboarding-new-resource-type.md` already uses KeyVault as its
   worked example for steps 1-2 (bootstrap). Add a short note after
   step 6 recording that KeyVault was carried all the way through for
   real (steps 3-6 done in
   `docs/plans/queue/2026-07-02-keyvault-tier-1.md`), without
   hardcoding a specific validated-check count in prose (same
   "don't reintroduce the 40-vs-41 confusion" reasoning as the Tier 2
   storage-buildout plan's Task 5).

2. If Task 3 found the array-typed-property gap in `rule_compile.md`
   to be real (a hypothesis genuinely got `rejected` because of it, not
   just theoretically possible), add a short section to
   `docs/patterns/rego-rule-authoring.md` (it already documents one
   Rego-authoring pitfall, the `==`-vs-`!=` one -- this would be a
   second, unrelated one, same file) describing the
   `some x in resource.properties.<array> { x.<field> == ... }` idiom
   and update `harness/workflows/prompts/rule_compile.md` to mention
   it. If every array-typed hypothesis validated cleanly, don't write
   this speculatively -- note in the commit message that it was
   checked and not needed, so a future reader doesn't wonder whether
   it was overlooked.

3. Commit: `"Document KeyVault Tier 1 results"` (or a more specific
   message if `rego-rule-authoring.md`/`rule_compile.md` were also
   updated).

## Open questions for whoever executes this plan

- **Tier 2 for KeyVault is out of scope here.** Once Tier 1 is solid,
  a `pattern_extract.md` for KeyVault and a
  `keyvault-pattern-tier.yaml` would follow the exact same shape as
  Storage's (see `docs/plans/complete/2026-07-02-tier-2-pattern-checks.md`
  and `docs/plans/queue/2026-07-02-tier-2-storage-buildout.md`) -- not
  started here, flagged the same way each prior plan flagged its own
  "next resource type" or "next tier" follow-up.
- **The array-typed-property question may turn out to not matter at
  all** if none of KeyVault's actually-relevant properties (per Task
  2's classification) end up being array-typed -- `networkAcls.ipRules[]`
  and `accessPolicies[].*` might get classified `relevant: false` on
  their own merits (e.g. "an individual IP rule isn't itself risky/safe,
  only the aggregate `defaultAction` is") rather than because of any
  Rego-authoring limitation. Don't treat "the array question" as
  something that must be resolved by this plan; let Task 2's real
  classifications and Task 3's real compile attempts settle it.
