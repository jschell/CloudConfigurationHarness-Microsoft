package checks.az_stor_pat_007

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.publicNetworkAccess == "Enabled"
    resource.properties.networkAcls.defaultAction == "Allow"
    msg := "Storage account has publicNetworkAccess=Enabled combined with networkAcls.defaultAction=Allow, making the data plane reachable from the entire internet with no network restriction whatsoever; either gate alone would still confine or block access."
}
