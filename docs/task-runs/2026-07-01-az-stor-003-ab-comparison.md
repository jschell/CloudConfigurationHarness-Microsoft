# A/B run comparison

Note: both runs share check_id 'AZ-STOR-003' -- rule/fixture status below reflects whichever run most recently wrote that row (no per-run history for those tables), not necessarily this run's own outcome. Adapter verdicts are correctly scoped per run.

## Run A (workflow_runs.id=2)
- workflow: storage-atomic-tier
- status: completed  (2026-07-01 21:35:03 -> 2026-07-01 21:35:47)
- models used: claude-opus-4-8, claude-sonnet-5
- check_id: AZ-STOR-003
- rule status: validated
- retries before terminal state: 0
- adapter verdicts:
  [PASS] rego_validate expected=fail actual=fail
  [PASS] rego_validate expected=pass actual=pass

## Run B (workflow_runs.id=3)
- workflow: storage-atomic-tier
- status: completed  (2026-07-01 21:36:13 -> 2026-07-01 21:36:42)
- models used: claude-opus-4-8, glm-5.2
- check_id: AZ-STOR-003
- rule status: validated
- retries before terminal state: 0
- adapter verdicts:
  [PASS] rego_validate expected=fail actual=fail
  [PASS] rego_validate expected=pass actual=pass

## Verdict agreement
Both runs reached the same outcome: validated.

## Rego rule diff (A -> B)
```diff
(both runs wrote the same rule_path -- run B overwrote run A's file; diff not meaningful, compare journal history instead)
```

## Manual qualitative diff (from snapshots taken between runs)

`compare_runs.py` can't diff the two rules once run B overwrites run A's
file on disk (both wrote `rules/azure/storage/AZ-STOR-003.rego`), so this
part was done by hand -- snapshotting each run's output before the next
run started.

```diff
--- claude-sonnet-5 (run A)
+++ glm-5.2 (run B)
 package main
 
+import rego.v1
+
+# AZ-STOR-003
+# Storage accounts should require HTTPS (secure transfer).
+# Hypothesis id 3: properties.supportsHttpsTrafficOnly == false is risky.
+# On older API versions the property may be absent and is treated as not enforced.
+#
+# Input is the compiled ARM template produced by `az bicep build`:
+# a top-level object with a `resources` array.
+
 deny contains msg if {
-	some resource in input.resources
-	resource.type == "Microsoft.Storage/storageAccounts"
-	resource.properties.supportsHttpsTrafficOnly == false
-	msg := "Storage account has supportsHttpsTrafficOnly set to false, permitting plaintext HTTP access to data-plane endpoints and exposing data and SAS tokens to interception. Set properties.supportsHttpsTrafficOnly to true to enforce TLS on all requests."
+    some resource in input.resources
+    resource.type == "Microsoft.Storage/storageAccounts"
+    not https_enforced(resource)
+    msg := "AZ-STOR-003: Storage account does not enforce HTTPS (supportsHttpsTrafficOnly should be true)."
+}
+
+# Safe configuration: explicitly set to true.
+https_enforced(resource) if {
+    resource.properties.supportsHttpsTrafficOnly == true
 }
```

Both fixtures/generation approaches passed both adapter checks
identically. The interesting difference is correctness under an edge case
neither fixture exercises: Claude's rule fires only when
`supportsHttpsTrafficOnly == false` explicitly; GLM's rule fires whenever
`https_enforced` is *not true*, which also covers the case its own
comment calls out -- pre-2019-04-01 API versions where the property may be
*absent* rather than `false`. Claude's `== false` check would not fire in
that case (comparing against an undefined field makes the expression
undefined, not true), so GLM's version is arguably the more robust rule
for the hypothesis as stated, even though nothing in the current fixture
pair would have caught the difference. That's a real finding from doing
this comparison, not a hypothetical one -- worth folding into
`rule_compile.md` in a future session (e.g. explicitly requiring
fixtures that cover an "absent property" case, not just true/false).