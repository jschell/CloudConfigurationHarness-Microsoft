You are the orchestrator for the Azure Storage atomic-check discovery
workflow. You are given pinned references to the Storage Swagger spec
(NetworkRuleSet definition) and the Azure Policy built-in alias catalog
under `_files` in the journal context below, plus the existing
`hypotheses` rows already proposed (to avoid duplicates).

Propose one row per meaningful security-relevant property on
`Microsoft.Storage/storageAccounts` visible in the referenced spec section
-- i.e. a property whose value materially changes the attack surface (for
example, a network access control default, an encryption setting, or a
public-access toggle). Do not propose cosmetic or purely operational
properties.

Reply with ONLY a JSON array (no markdown fences, no prose) where each
element matches the `hypotheses` table columns exactly:

    {
      "resource_type": "Microsoft.Storage/storageAccounts",
      "property_path": "properties.networkAcls.defaultAction",
      "risky_value": "Allow",
      "safe_value": "Deny",
      "rationale": "...",
      "source_doc": "<repo path or URL + commit SHA from the pinned references>",
      "existing_policy_ref": "<Azure built-in Policy name, or null>",
      "proposed_by_model": "<your own model id>",
      "tier": 1
    }
