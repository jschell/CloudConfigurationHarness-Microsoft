package checks.az_kv_004

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    some policy in resource.properties.accessPolicies
    some permission in policy.permissions.keys
    permission == "all"
    msg := sprintf("Key Vault '%s' grants the broad 'all' key permission to a principal in an access policy; scope key data-plane rights to a least-privilege subset (e.g. get, list) excluding purge and unneeded cryptographic-use grants", [resource.name])
}
