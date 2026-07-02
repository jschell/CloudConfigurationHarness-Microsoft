package checks.az_stor_025

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.encryption.services.queue.keyType != "Account"
    msg := sprintf("AZ-STOR-020: Storage account '%s' uses queue encryption keyType '%v'; Account-scoped keys are required for stronger key isolation and customer-controlled rotation.", [resource.name, resource.properties.encryption.services.queue.keyType])
}
