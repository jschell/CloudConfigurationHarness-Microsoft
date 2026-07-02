package checks.az_stor_004

import rego.v1

# AZ-STOR-004
# Storage accounts should enforce a minimum TLS version of 1.2.
# Hypothesis id 4: properties.minimumTlsVersion should be "TLS1_2"; any
# other value is risky. When unset, the property defaults to TLS1_0.
#
# Originally written as `== "TLS1_0"`, which missed TLS1_1 (also
# deprecated and vulnerable) entirely -- confirmed live: a fixture with
# minimumTlsVersion "TLS1_1" incorrectly evaluated as "pass" under the
# old rule. Rewritten to deny on the negation of the known-safe value
# instead of enumerating one risky value, which is the right default
# whenever a property has more than one bad value (TLS1_3 is listed in
# the swagger enum but documented as "not supported" for this property,
# so treating it as risky alongside TLS1_0/TLS1_1 is correct too).
# See docs/patterns/rego-rule-authoring.md for the general pattern.
#
# Input is the compiled ARM template produced by `az bicep build`:
# a top-level object with a `resources` array.

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.minimumTlsVersion != "TLS1_2"
    msg := "AZ-STOR-004: Storage account does not enforce minimumTlsVersion TLS1_2 or higher."
}
