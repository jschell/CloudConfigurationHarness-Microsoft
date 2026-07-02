package checks.az_stor_020

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.encryption.services.queue.keyType == "Service"
    msg := "Storage account encryption queue service keyType is 'Service'; use 'Account'-scoped keys for stronger isolation and customer-controlled rotation"
}
