package checks.az_kv_017

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    not resource.properties.softDeleteRetentionInDays >= 90
    msg := sprintf("Key Vault '%s' has a soft-delete retention period below the 90-day maximum (properties.softDeleteRetentionInDays); a minimal retention window shortens the ability to recover from malicious or accidental deletion (e.g. an attacker or ransomware purging secrets). Set it to 90 for the strongest recovery posture.", [resource.name])
}