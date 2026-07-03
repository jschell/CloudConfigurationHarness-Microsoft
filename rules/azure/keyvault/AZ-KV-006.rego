package checks.az_kv_006

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.enablePurgeProtection == false
    msg := sprintf("Key Vault '%s' has purge protection disabled; set properties.enablePurgeProtection to true so that deleted keys/secrets/certificates cannot be permanently purged before the soft-delete retention period elapses", [resource.name])
}
