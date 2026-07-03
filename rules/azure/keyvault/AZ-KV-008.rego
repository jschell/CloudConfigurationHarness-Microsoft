package checks.az_kv_008

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.enableSoftDelete == false
    msg := sprintf("Key Vault '%s' has soft delete disabled; set properties.enableSoftDelete to true so that deleted keys/secrets/certificates can be recovered within the retention period", [resource.name])
}
