package checks.az_stor_029

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.isNfsV3Enabled == true
    msg := "Storage account has NFSv3 protocol support enabled, exposing an unauthenticated-by-default network filesystem endpoint that lacks encryption and relies solely on IP/network ACLs for access control"
}
