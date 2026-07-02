package checks.az_stor_026

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.immutableStorageWithVersioning.immutabilityPolicy.state == "Unlocked"
    msg := "Storage account has an Unlocked immutability policy, which can be weakened or removed, defeating WORM protection and compliance enforcement. Set immutableStorageWithVersioning.immutabilityPolicy.state to Locked."
}
