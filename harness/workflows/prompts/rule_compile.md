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

Start the file with the literal line `package PLACEHOLDER` -- the harness
replaces it with the correct `checks.<check_id>` namespace after you
reply (you are not told the check_id in advance; see below for why). Do
NOT use `package main`. The adapter's `--policy <rules directory>` loads
every check's .rego file in that directory at once; if two checks shared
one namespace, testing
one check's fixture would also evaluate every other check's `deny` rules
against it, and a new rule could silently break an older, already-
validated check's fixtures. Each check gets its own package specifically
to prevent that.

The input document is the full compiled ARM template JSON produced by `az
bicep build` -- a top-level object with a `resources` array, NOT a bare
single-resource object. Iterate it, e.g.:

    deny contains msg if {
        some resource in input.resources
        resource.type == "<hypothesis resource_type>"
        resource.properties.<hypothesis property_path minus "properties."> == "<risky_value>"
        msg := "..."
    }

**Prefer denying on the negation of `safe_value` (`!= "<safe_value>"`)
over matching one `risky_value` (`== "<risky_value>"`) whenever the
property's enum has more than two possible values, or the hypothesis
describes a threshold/minimum (e.g. a TLS/API version).** A single
`== risky_value` check only catches that one value -- if the enum has
other equally-bad values (e.g. `minimumTlsVersion`'s `TLS1_0` AND
`TLS1_1` are both deprecated, but a rule written as `== "TLS1_0"` misses
`TLS1_1` entirely), those slip through undetected. This isn't
hypothetical: exactly that bug shipped in AZ-STOR-004 and was only
caught by hand later. `== risky_value` is fine when the property is
strictly binary (e.g. `networkAcls.defaultAction` only has `Allow`/
`Deny`) since there's nothing else it could be. Full writeup:
`docs/patterns/rego-rule-authoring.md`.

**If the target hypothesis's `property_conditions` field is non-null**
(a Tier 2 / combination hypothesis -- `tier` will be 2), it is a JSON
list of `{property_path, risky_value, safe_value}` objects. The rule
must deny only when ALL conditions are in their risky state
simultaneously (a plain Rego rule body is an implicit AND across its
statements, so this is just one condition per property, same syntax
as a Tier 1 rule):

    deny contains msg if {
        some resource in input.resources
        resource.type == "<hypothesis resource_type>"
        resource.properties.<condition 1 property> == "<condition 1 risky_value>"
        resource.properties.<condition 2 property> == "<condition 2 risky_value>"
        msg := "..."
    }

Do not use `!=`/negation tricks to combine conditions unless a
specific condition's own semantics call for it (same guidance as
single-property rules -- see docs/patterns/rego-rule-authoring.md).
Every condition must be explicit; the rule must NOT fire when only
some (not all) of the conditions are risky -- that's what the "mixed"
fixture variants (see fixture_generate.md) exist to prove.

Do NOT invent a check_id or rule_path yourself, and don't include them in
your reply -- the harness assigns the check_id deterministically (see
`docs/patterns/deterministic-check-id-assignment.md`). Each call to you is
a stateless invocation with no memory of other calls, so you have no
reliable way to know which numbers are already taken; a model-invented
check_id previously collided with an already-validated check and silently
overwrote it (2026-07-02) before this fix.

Reply with ONLY a JSON object (no markdown fences, no prose):

    {
      "hypothesis_id": <id of the hypothesis row you compiled>,
      "rego_content": "<the full .rego file contents as a string, starting with 'package PLACEHOLDER'>"
    }
