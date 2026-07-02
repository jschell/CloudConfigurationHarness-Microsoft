package checks.az_stor_016

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.encryption.identity.userAssignedIdentity == ""
    msg := "storage account encryption.identity.userAssignedIdentity is empty; a user-assigned identity ARM resource id is required to correctly bind the customer-managed-key (CMK) encryption identity"
}
