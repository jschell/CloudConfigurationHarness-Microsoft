package checks.az_stor_pat_003

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.supportsHttpsTrafficOnly == false
    resource.properties.allowSharedKeyAccess == true
    msg := "Storage account permits plaintext HTTP while Shared Key access is enabled, exposing the long-lived, unrotatable account key in cleartext on the wire and enabling full account takeover from network eavesdropping."
}
