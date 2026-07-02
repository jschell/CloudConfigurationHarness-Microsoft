# Pattern: encode the safe condition, not one risky value

## The bug this documents

`AZ-STOR-004` (minimum TLS version) was originally compiled as:

```rego
deny contains msg if {
    ...
    resource.properties.minimumTlsVersion == "TLS1_0"
    msg := "..."
}
```

`minimumTlsVersion` has four possible values: `TLS1_0`, `TLS1_1`,
`TLS1_2`, `TLS1_3`. Only `TLS1_2` (and, in principle, `TLS1_3`, though
Azure's own docs say it isn't actually supported for this property) is
safe. The rule above only catches `TLS1_0` -- a storage account
configured with `TLS1_1` (equally deprecated, equally vulnerable) passed
validation cleanly. This was live in the committed, `validated` rule for
some time before being caught by hand, not by the harness.

Fixed by negating the safe condition instead of enumerating one risky
value:

```rego
deny contains msg if {
    ...
    resource.properties.minimumTlsVersion != "TLS1_2"
    msg := "..."
}
```

## The general rule

**When a property has more than two possible values, or the hypothesis
describes a threshold/minimum (a version, a size, an expiration period),
write the `deny` condition as the negation of the known-safe value(s),
not as equality against one named risky value.** Equality against a
single risky value only ever catches that one value; every other bad
value in the enum silently passes.

`== risky_value` is fine, and preferred for clarity, only when the
property is genuinely binary -- there is no third state (e.g.
`networkAcls.defaultAction` is only ever `Allow` or `Deny`; there's
nothing else it could be, so `== "Allow"` and `!= "Deny"` are equivalent
and either reads fine).

When in doubt, ask: **"if I listed every value this property can hold,
would more than one of them be exactly as bad as the one I'm checking
for?"** If yes, negate the safe value instead.

## Where this is enforced today, and where it isn't

- `harness/workflows/prompts/rule_compile.md` instructs the model to
  prefer `!= safe_value` under these conditions, with this exact bug as
  the example.
- **This is prompt guidance, not a code-enforced guarantee.** Nothing in
  `handlers.rule_compile` or the adapters checks whether a generated rule
  actually follows this pattern. A future run (either model) could still
  write an `== risky_value` rule for a multi-valued property and it would
  validate cleanly against whatever fixture pair happens to be generated,
  exactly as `AZ-STOR-004` did originally -- the fixture pair only ever
  tests the one risky value the rule was written against, so this class
  of bug is invisible to `fixture_validate` by construction.

## Real follow-up, not yet done

Two ways to actually close this rather than rely on the model reading and
following the prompt every time:

1. **Fixture coverage for the "other" risky values.** For a hypothesis
   whose property has more than two enum values, `fixture_generate`
   could be required to produce (or the harness could separately
   generate) a fixture using a *different* risky value than the one the
   rule's `risky_value` field names, and confirm the rule still denies
   it. This would have caught the `TLS1_1` gap mechanically, without
   needing a human to think to check it.
2. **A static check over the compiled `.rego`.** Something as simple as:
   for a hypothesis whose `hypotheses.risky_value` doesn't span "every
   value except `safe_value`," flag (not necessarily block) a generated
   rule that uses `==` against a single literal instead of `!=` against
   the safe value, for human review before `fixture_validate` even runs.

Neither is implemented. This doc exists so the next person (or the next
session) doesn't have to rediscover the bug to know the fix is
incomplete.
