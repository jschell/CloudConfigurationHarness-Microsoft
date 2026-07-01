You compile one Azure configuration attack-path hypothesis into a Rego
rule. The journal context below includes the `hypotheses` table rows and
`_run_context`, which carries `target_hypothesis_id` (the hypothesis row
you must compile this run) and, on a retry, `last_failure_reason` (why the
previous attempt's fixtures failed validation -- fix the rule accordingly).

Write a `package main` Rego policy with a `deny[msg]` rule that fires when
the resource is in its risky configuration (per the hypothesis's
`risky_value`) and does not fire when it is in its safe configuration
(`safe_value`). The input document is the compiled ARM-export-shaped JSON
for a single resource (top-level `type` and `properties`, matching the
hypothesis's `resource_type` and `property_path`).

Pick a check_id of the form `AZ-STOR-NNN` (three digits, next unused
number for this resource type) and a rule_path of
`rules/azure/storage/<check_id>.rego`.

Reply with ONLY a JSON object (no markdown fences, no prose):

    {
      "hypothesis_id": <id of the hypothesis row you compiled>,
      "check_id": "AZ-STOR-NNN",
      "rule_path": "rules/azure/storage/AZ-STOR-NNN.rego",
      "rego_content": "<the full .rego file contents as a string>"
    }
