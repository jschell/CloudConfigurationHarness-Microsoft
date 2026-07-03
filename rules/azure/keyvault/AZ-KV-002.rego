package checks.az_kv_002

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    some policy in resource.properties.accessPolicies
    some permission in policy.permissions.certificates
    permission == "all"
    msg := sprintf("Key Vault '%s' grants the broad 'all' certificate permission to a principal in an access policy; scope certificate data-plane rights to a least-privilege subset (e.g. get, list) excluding purge/manageissuers", [resource.name])
}
