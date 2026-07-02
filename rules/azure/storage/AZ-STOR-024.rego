package checks.az_stor_024

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    not resource.properties.immutableStorageWithVersioning.enabled
    msg := "Storage account should enable immutable storage with versioning (properties.immutableStorageWithVersioning.enabled) for tamper-resistance and ransomware protection"
}