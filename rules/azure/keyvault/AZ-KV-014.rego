package checks.az_kv_014

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    some rule in resource.properties.networkAcls.ipRules
    rule.value == "0.0.0.0/0"
    msg := "Key Vault networkAcls.ipRules contains a 0.0.0.0/0 (any IPv4) entry, which re-opens the vault to the public internet and defeats the default-deny network ACL posture."
}
