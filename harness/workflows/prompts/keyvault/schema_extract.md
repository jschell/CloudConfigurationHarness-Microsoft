You are the orchestrator for the Microsoft.KeyVault/vaults atomic-check discovery
workflow. Under `_files` in the journal context below you're given:

- `sources/azure/keyvault/keyvault-properties.enumerated.json` -- a deterministically generated,
  EXHAUSTIVE list of every property on `Microsoft.KeyVault/vaults`
  (`.properties.property_count` entries under `.properties`). This is
  not curated or filtered; it includes obviously operational/read-only
  properties on purpose.
- `sources/azure/keyvault/keyvault-policy-refs.md` -- narrative context and the existing Azure
  Policy built-in catalog, for grounding `existing_policy_ref`.

You're also given the current `hypotheses` and `schema_coverage` table
rows already recorded.

Your job is to classify EVERY property in the enumerated list that is
NOT already present in `schema_coverage` (match on `property_path`) --
do not re-classify ones already covered, and do not skip any of the
remaining ones just because they look boring. For each one, decide:

- **Relevant**: the property's value materially changes the attack
  surface (a network access control default, an encryption setting, an
  auth/public-access toggle, etc.).
- **Not relevant**: cosmetic, purely operational/informational (e.g. a
  read-only endpoint URL, a provisioning-state field, a timestamp), or a
  property whose values don't meaningfully differ in security posture.

This exhaustiveness is the point: `schema_coverage` is the record of
"every property we've ever considered and why we did or didn't act on
it," not just the interesting ones. A large fraction of the enumerated
list will legitimately be "not relevant" -- classify them anyway, with a
one-sentence rationale each. Don't skip properties to save output length.

Reply with ONLY a JSON array (no markdown fences, no prose), one element
per property you're classifying:

Relevant property:

    {
      "resource_type": "Microsoft.KeyVault/vaults",
      "property_path": "properties.someAccessControlSetting",
      "relevant": true,
      "risky_value": "<the value that widens the attack surface>",
      "safe_value": "<the value that narrows it>",
      "rationale": "...",
      "source_doc": "<repo path or URL + commit SHA from the pinned references>",
      "existing_policy_ref": "<Azure built-in Policy name, or null>",
      "proposed_by_model": "<your own model id>",
      "tier": 1
    }

Not-relevant property (no risky_value/safe_value/source_doc/
existing_policy_ref/proposed_by_model/tier needed):

    {
      "resource_type": "Microsoft.KeyVault/vaults",
      "property_path": "properties.someReadOnlyTimestamp",
      "relevant": false,
      "rationale": "Read-only informational field, not a configurable security control."
    }
