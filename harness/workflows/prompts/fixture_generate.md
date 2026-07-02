You generate a fixture pair for a compiled Rego rule. The journal context
below includes the `rules` table rows (find the one matching
`_run_context.check_id`) and the corresponding `rego_content` you (or a
prior attempt) wrote.

Write two minimal, self-contained Bicep templates for the same resource
type as the rule:

- `vulnerable.bicep`: the resource configured with the hypothesis's risky
  value, so the rule's `deny` fires against it.
- `safe.bicep`: the same resource configured with the safe value, so the
  rule's `deny` does not fire against it.

Keep both templates minimal -- only the properties needed to exercise the
rule, plus whatever `resource` boilerplate Bicep requires to be valid
(apiVersion, name, location, sku/kind if required by the resource type).

Cite a `ground_truth_method` for why the vulnerable/safe labels are correct
(e.g. "azure-policy-builtin" if an existing Azure Policy built-in
definition already flags this exact configuration, or "manual-expert" with
your rationale in `ground_truth_ref` otherwise).

Do not include check_id or fixture_dir in your reply -- the harness
already knows which check this fixture pair belongs to (see
`docs/patterns/deterministic-check-id-assignment.md`) and writes the
files to the right place itself.

Reply with ONLY a JSON object (no markdown fences, no prose):

    {
      "vulnerable_bicep": "<full .bicep file contents>",
      "safe_bicep": "<full .bicep file contents>",
      "ground_truth_method": "azure-policy-builtin | manual-expert | iam-simulator",
      "ground_truth_ref": "<policy definition ID or reviewer name, or null>"
    }
