package checks.az_stor_019

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.encryption.services.file.keyType != "Account"
    msg := "File service encryption should use account-scoped keys (keyType=Account), not the shared service-default key, for stronger isolation and customer-controlled rotation."
}
