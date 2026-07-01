package main

import rego.v1

# AZ-STOR-003
# Storage accounts should require HTTPS (secure transfer).
# Hypothesis id 3: properties.supportsHttpsTrafficOnly == false is risky.
# On older API versions the property may be absent and is treated as not enforced.
#
# Input is the compiled ARM template produced by `az bicep build`:
# a top-level object with a `resources` array.

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    not https_enforced(resource)
    msg := "AZ-STOR-003: Storage account does not enforce HTTPS (supportsHttpsTrafficOnly should be true)."
}

# Safe configuration: explicitly set to true.
https_enforced(resource) if {
    resource.properties.supportsHttpsTrafficOnly == true
}
