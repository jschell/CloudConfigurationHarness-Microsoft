You compile one Azure configuration attack-path hypothesis into a Rego
rule. The journal context below includes the `hypotheses` table rows and
`_run_context`, which carries `target_hypothesis_id` (the hypothesis row
you must compile this run) and, on a retry, `last_failure_reason` (why the
previous attempt's fixtures failed validation -- fix the rule accordingly).

Write a Rego policy targeting Rego v1 syntax (the `opa`/`conftest`
versions this harness validates against default to v1) with a `deny
contains msg if { ... }` rule -- not the older `deny[msg] { ... }` form,
which fails to parse under v1 (`if`/`contains` keywords are required).
The rule fires when the resource is in its risky configuration (per the
hypothesis's `risky_value`) and does not fire when it is in its safe
configuration (`safe_value`).

The package MUST be `checks.<check_id lowercased, dashes to underscores>`
-- e.g. check_id `AZ-STOR-005` gets `package checks.az_stor_005` -- NOT
`package main`. `--policy rules/azure/storage/` loads every check's
.rego file at once; if two checks shared `package main`, testing one
check's fixture would also evaluate every other check's `deny` rules
against it, and a new rule could silently break an older, already-
validated check's fixtures. Each check gets its own package specifically
to prevent that (`rego_validate.py` queries the matching namespace via
`--namespace`, keyed off check_id, so this convention is load-bearing --
don't deviate from it).

The input document is the full compiled ARM template JSON produced by `az
bicep build` -- a top-level object with a `resources` array, NOT a bare
single-resource object. Iterate it, e.g.:

    deny contains msg if {
        some resource in input.resources
        resource.type == "<hypothesis resource_type>"
        resource.properties.<hypothesis property_path minus "properties."> == "<risky_value>"
        msg := "..."
    }

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
