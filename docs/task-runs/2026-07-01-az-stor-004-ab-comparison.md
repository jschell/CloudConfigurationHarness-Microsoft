# A/B run comparison

**Important correction, added after the fact:** both runs below "failed"
for the same reason -- at the time they ran, every check's `.rego` file
shared `package main`, so `conftest --policy rules/azure/storage/`
evaluated ALL checks' `deny` rules against every fixture. AZ-STOR-003's
rule (from the previous A/B) fires on the *absence* of
`supportsHttpsTrafficOnly`, and neither run's AZ-STOR-004 fixtures set
that property, so both runs' "safe" fixture spuriously failed for a
reason that has nothing to do with AZ-STOR-004 or minimumTlsVersion at
all. This was a harness bug (see the 2026-07-01 status doc, Session 5),
fixed by giving each check its own Rego package/conftest namespace.

**Re-tested both rules in isolation after the fix**: both run A's and run
B's final `rego_content` pass cleanly (`vulnerable -> fail`,
`safe -> pass`) once evaluated under their own namespace instead of the
shared one. Run B's 3 retries and eventual `rejected` status below were
therefore a false negative caused entirely by the harness bug, not a
defect in GLM's rule or fixture -- worth knowing before drawing any
"which model is better" conclusion from the raw numbers below.

## Run A (workflow_runs.id=5)
- workflow: storage-atomic-tier
- status: completed  (2026-07-01 22:44:35 -> 2026-07-01 22:49:29)
- models used: claude-opus-4-8, claude-sonnet-5
- check_id: AZ-STOR-004
- validated (this run's own adapter checks): False
- retries before terminal state: 1
- last failure reason: ['rego_validate: expected=pass actual=fail', 'rego_validate: expected=fail actual=fail']
- adapter verdicts:
  [PASS] rego_validate expected=fail actual=fail
  [FAIL] rego_validate expected=pass actual=fail
  [PASS] rego_validate expected=fail actual=fail
  [PASS] rego_validate expected=pass actual=pass

## Run B (workflow_runs.id=6)
- workflow: storage-atomic-tier
- status: completed  (2026-07-01 22:50:36 -> 2026-07-01 22:53:12)
- models used: claude-opus-4-8, glm-5.2
- check_id: AZ-STOR-004
- validated (this run's own adapter checks): False
- retries before terminal state: 3
- last failure reason: ['rego_validate: expected=pass actual=fail', 'rego_validate: expected=fail actual=fail']
- adapter verdicts:
  [PASS] rego_validate expected=fail actual=fail
  [FAIL] rego_validate expected=pass actual=fail
  [PASS] rego_validate expected=fail actual=fail
  [FAIL] rego_validate expected=pass actual=fail
  [PASS] rego_validate expected=fail actual=fail
  [FAIL] rego_validate expected=pass actual=fail

## Verdict agreement
Both runs reached the same outcome: not validated.

## Rego rule diff (A -> B)
```diff
--- run A: rules/azure/storage/AZ-STOR-004.rego
+++ run B: rules/azure/storage/AZ-STOR-004.rego
@@ -3,17 +3,27 @@
 import rego.v1
 
 # AZ-STOR-004
-# Storage accounts should enforce a minimum TLS version of 1.2.
-# Hypothesis id 4: properties.minimumTlsVersion == "TLS1_0" is risky.
-# When unset, the property defaults to TLS1_0, permitting deprecated and
-# vulnerable TLS protocol versions to be negotiated for data-plane requests.
+# Hypothesis id 4: Microsoft.Storage/storageAccounts
+# properties.minimumTlsVersion
+#   risky_value: "TLS1_0"  (and other deprecated versions)
+#   safe_value:  "TLS1_2"
 #
-# Input is the compiled ARM template produced by `az bicep build`:
-# a top-level object with a `resources` array.
+# minimumTlsVersion defaults to TLS 1.0 when unset. TLS 1.0/1.1 are deprecated
+# and vulnerable to known downgrade and cryptographic attacks (BEAST, weak
+# cipher negotiation). Enforcing a minimum of TLS 1.2 rejects clients
+# negotiating obsolete protocol versions.
+#
+# This rule fires only when a storage account explicitly sets
+# minimumTlsVersion to the risky value "TLS1_0". It does not fire on the safe
+# value "TLS1_2", nor when the property is absent (absence is not treated as
+# risky here).
+#
+# Input is the full compiled ARM template produced by `az bicep build` -- a
+# top-level object with a `resources` array.
 
 deny contains msg if {
-    some resource in input.resources
-    resource.type == "Microsoft.Storage/storageAccounts"
-    resource.properties.minimumTlsVersion == "TLS1_0"
-    msg := "AZ-STOR-004: Storage account allows TLS 1.0 (minimumTlsVersion should be TLS1_2)."
+	some resource in input.resources
+	resource.type == "Microsoft.Storage/storageAccounts"
+	resource.properties.minimumTlsVersion == "TLS1_0"
+	msg := sprintf("AZ-STOR-004: Storage account '%s' has minimumTlsVersion set to 'TLS1_0'; require TLS1_2 to reject deprecated, cryptographically weak TLS protocol versions", [resource.name])
 }

```