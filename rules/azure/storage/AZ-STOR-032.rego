package checks.az_stor_032

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    some rule in resource.properties.networkAcls.ipRules
    rule.value == "0.0.0.0/0"
    msg := "Storage account networkAcls.ipRules contains a 0.0.0.0/0 (any IPv4) entry, which re-opens the account to the public internet and defeats the default-deny network ACL posture."
}
