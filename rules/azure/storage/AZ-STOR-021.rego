package checks.az_stor_021

import rego.v1

# AZ-STOR-021
# Storage accounts with account-level immutable (WORM) storage must enforce
# a meaningful immutability retention window.
# Hypothesis id 24: properties.immutableStorageWithVersioning.immutabilityPolicy
# .immutabilityPeriodSinceCreationInDays defines the WORM retention period.
# A value of 0 (or unset, when the immutability policy is otherwise configured)
# effectively disables the retention guarantee, allowing premature deletion of
# regulated data and undermining compliance / tamper-protection.
#
# Written as a threshold (deny when the period is < 1 day) rather than matching
# the single risky_value "0", because the hypothesis describes a minimum
# retention requirement: any sub-threshold value (0, or absent) is risky.
# See docs/patterns/rego-rule-authoring.md for the threshold pattern.
#
# Input is the compiled ARM template produced by `az bicep build`: a top-level
# object with a `resources` array. We only evaluate accounts that actually
# configure an immutabilityPolicy; accounts without versioned immutable
# storage are out of scope for this check (handled separately if needed).

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    policy := resource.properties.immutableStorageWithVersioning.immutabilityPolicy
    days := policy.immutabilityPeriodSinceCreationInDays
    days < 1
    msg := sprintf("AZ-STOR-021: Storage account immutable storage policy has immutabilityPeriodSinceCreationInDays=%v; enforce a non-zero WORM retention window (>= required retention)", [days])
}
