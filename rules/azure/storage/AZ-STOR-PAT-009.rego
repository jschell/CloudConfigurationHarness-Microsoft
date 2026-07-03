package checks.az_stor_pat_009

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.allowSharedKeyAccess == true
    resource.properties.defaultToOAuthAuthentication == false
    msg := "Storage account permits Shared Key access while OAuth (Entra ID) is not the default authentication method, making the long-lived, unscoped account key the path of least resistance for default-configured clients and maximizing unattributable key usage."
}
