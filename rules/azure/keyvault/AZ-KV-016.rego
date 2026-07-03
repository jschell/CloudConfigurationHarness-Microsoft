package checks.az_kv_016

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.KeyVault/vaults"
	resource.properties.publicNetworkAccess == "Enabled"
	msg := "Key Vault is reachable over the public internet; set properties.publicNetworkAccess to 'Disabled' to restrict access to private endpoints and trusted-service traffic only."
}
