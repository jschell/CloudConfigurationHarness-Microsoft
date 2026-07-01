package checks.az_stor_004

import rego.v1

# AZ-STOR-004
# Storage accounts should enforce a minimum TLS version of 1.2.
# Hypothesis id 4: properties.minimumTlsVersion == "TLS1_0" is risky.
# When unset, the property defaults to TLS1_0, permitting deprecated and
# vulnerable TLS protocol versions to be negotiated for data-plane requests.
#
# Input is the compiled ARM template produced by `az bicep build`:
# a top-level object with a `resources` array.

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.minimumTlsVersion == "TLS1_0"
    msg := "AZ-STOR-004: Storage account allows TLS 1.0 (minimumTlsVersion should be TLS1_2)."
}
