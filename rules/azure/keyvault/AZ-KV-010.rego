package checks.az_kv_010

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.enabledForDiskEncryption == true
    msg := sprintf("Key Vault '%s' has enabledForDiskEncryption enabled; set properties.enabledForDiskEncryption to false so that the Azure Disk Encryption flow cannot retrieve secrets and unwrap keys from the vault unless disk encryption against this vault is actually in use", [resource.name])
}
