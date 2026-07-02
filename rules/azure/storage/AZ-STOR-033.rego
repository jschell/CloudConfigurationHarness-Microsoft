package checks.az_stor_033

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    some rule in resource.properties.networkAcls.ipv6Rules
    rule.value == "::/0"
    msg := "Storage account networkAcls.ipv6Rules contains a ::/0 (any IPv6) entry, which re-opens the account to the public IPv6 internet and defeats the default-deny network ACL posture."
}
