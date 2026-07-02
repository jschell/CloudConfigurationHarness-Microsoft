You are classifying a batch of properties on an Azure resource type for
security relevance, as part of a systematic sweep to completion (see
docs/patterns/schema-coverage-discovery.md). You are given supplementary
context (policy catalog, narrative docs) under `_files`, plus the
`resource_type` and the exact list of properties to classify this batch
under `_run_context.batch`. Every property in `batch` has already been
confirmed NOT YET classified -- do not skip any of them, and do not
classify anything outside this batch.

For each property, decide:

- **Relevant**: the property's value materially changes the attack
  surface (a network access control default, an encryption setting, an
  auth/public-access toggle, etc.).
- **Not relevant**: cosmetic, purely operational/informational (e.g. a
  read-only endpoint URL, a provisioning-state field, a timestamp), or a
  property whose values don't meaningfully differ in security posture.

Reply with ONLY a JSON array (no markdown fences, no prose), exactly one
element per property in `batch`, in the same order:

Relevant property:

    {
      "resource_type": "<the resource_type given>",
      "property_path": "<the property_path from batch>",
      "relevant": true,
      "risky_value": "Allow",
      "safe_value": "Deny",
      "rationale": "...",
      "source_doc": "<repo path or URL + commit SHA from the pinned references, or this batch's source_note if no more specific reference applies>",
      "existing_policy_ref": "<Azure built-in Policy name, or null>",
      "proposed_by_model": "<your own model id>",
      "tier": 1
    }

Not-relevant property (no risky_value/safe_value/source_doc/
existing_policy_ref/proposed_by_model/tier needed):

    {
      "resource_type": "<the resource_type given>",
      "property_path": "<the property_path from batch>",
      "relevant": false,
      "rationale": "Read-only informational endpoint URL, not a configurable security control."
    }
