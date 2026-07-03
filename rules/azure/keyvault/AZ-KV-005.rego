package checks.az_kv_005

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    some policy in resource.properties.accessPolicies
    some permission in policy.permissions.storage
    permission == "all"
    msg := sprintf("Key Vault '%s' grants the broad 'all' storage permission to a principal in an access policy; scope managed-storage data-plane rights to a least-privilege subset excluding key/SAS management (regeneratekey, setsas, purge)", [resource.name])
}
