package checks.az_stor_007

import rego.v1

# AZ-STOR-007
# Storage accounts should enable infrastructure (double) encryption at rest.
# Hypothesis id 8: properties.encryption.requireInfrastructureEncryption == false
# is risky. When only single-layer platform-managed encryption is applied, a flaw
# or key compromise in that single layer exposes plaintext; setting it to true
# applies a second, independent layer of platform-managed encryption for defense
# in depth.
#
# Input is the compiled ARM template produced by `az bicep build`:
# a top-level object with a `resources` array.

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.encryption.requireInfrastructureEncryption == false
	msg := "AZ-STOR-007: Storage account lacks infrastructure (double) encryption; set properties.encryption.requireInfrastructureEncryption to true for defense-in-depth encryption at rest."
}
