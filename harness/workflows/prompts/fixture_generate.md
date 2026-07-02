You generate fixture variants for a compiled Rego rule. The journal context
below includes the `rules` table row (find the one matching
`_run_context.check_id`), the corresponding `rego_content` you (or a prior
attempt) wrote, and the `hypotheses` row it was compiled from.

Write minimal, self-contained Bicep templates for the same resource type as
the rule -- one per variant needed to prove the rule is correct:

- If the hypothesis has a single `risky_value`/`safe_value` pair (Tier 1,
  `property_conditions` is null), write exactly two variants: a
  `"vulnerable"` one (expected_verdict `"fail"`) with the risky value, and a
  `"safe"` one (expected_verdict `"pass"`) with the safe value.
- If the hypothesis has multiple `property_conditions` (Tier 2, a pattern
  across more than one property), write one variant per combination worth
  covering: at minimum, all-risky-values (expected `"fail"`) and
  all-safe-values (expected `"pass"`), plus any combination where the
  properties individually look safe but the *combination* is risky (or vice
  versa) -- that combination is the whole point of a Tier 2 rule, so a
  fixture set that never exercises it doesn't actually test anything a
  Tier 1 rule couldn't already. Label each variant descriptively (e.g.
  `"public-network-and-open-firewall"`, not `"variant-3"`).

Keep every template minimal -- only the properties needed to exercise the
rule, plus whatever `resource` boilerplate Bicep requires to be valid
(apiVersion, name, location, sku/kind if required by the resource type).

Cite a `ground_truth_method` for why the labels are correct (e.g.
"azure-policy-builtin" if an existing Azure Policy built-in definition
already flags this exact configuration, or "manual-expert" with your
rationale in `ground_truth_ref` otherwise).

Do not include check_id or fixture_dir in your reply -- the harness already
knows which check this fixture set belongs to (see
docs/patterns/deterministic-check-id-assignment.md) and writes the files to
the right place itself.

Reply with ONLY a JSON object (no markdown fences, no prose):

    {
      "variants": [
        {"label": "vulnerable", "expected_verdict": "fail", "bicep": "<full .bicep file contents>"},
        {"label": "safe", "expected_verdict": "pass", "bicep": "<full .bicep file contents>"}
      ],
      "ground_truth_method": "azure-policy-builtin | manual-expert | iam-simulator",
      "ground_truth_ref": "<policy definition ID or reviewer name, or null>"
    }
