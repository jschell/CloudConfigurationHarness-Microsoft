package checks.az_stor_018

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.encryption.services.blob.keyType == "Service"
    msg := "AZ-STOR-018: Storage account blob encryption uses Service-scoped keys instead of Account-scoped keys; account-scoped keys provide stronger isolation and reduce the blast radius of key compromise."
}
