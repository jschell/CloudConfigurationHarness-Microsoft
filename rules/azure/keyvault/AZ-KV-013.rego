package checks.az_kv_013

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.networkAcls.defaultAction == "Allow"
    msg := sprintf("Key Vault '%s' has networkAcls.defaultAction set to Allow, opening the vault to all networks with the firewall effectively off; set properties.networkAcls.defaultAction to 'Deny' to restrict access to explicitly allowed IP ranges and virtual networks", [resource.name])
}
