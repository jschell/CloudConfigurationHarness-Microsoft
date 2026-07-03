package checks.az_kv_012

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.networkAcls.bypass == "AzureServices"
    msg := sprintf("Key Vault '%s' has networkAcls.bypass set to AzureServices, allowing trusted Azure platform services to bypass the configured network firewall rules; set properties.networkAcls.bypass to 'None' to enforce the firewall ACLs for all traffic", [resource.name])
}
