package checks.az_stor_pat_010

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.immutableStorageWithVersioning.enabled
    resource.properties.immutableStorageWithVersioning.immutabilityPolicy.state == "Unlocked"
    msg := "Storage account has immutableStorageWithVersioning.enabled=true but immutabilityPolicy.state=Unlocked, so the advertised WORM/ransomware protection does not actually hold -- an Unlocked policy can be weakened or removed by any principal with management-plane rights, allowing 'protected' data to be deleted or overwritten. Set immutabilityPolicy.state to Locked to make the immutability guarantee irreversible."
}
