package checks.az_stor_042

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.allowSharedKeyAccess == true
    resource.properties.networkAcls.defaultAction == "Allow"
    msg := "Storage account has Shared Key access enabled while network ACL default action is Allow, allowing unauthenticated-network reachability combined with an unscoped, unattributable long-lived credential"
}