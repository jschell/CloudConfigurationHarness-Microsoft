package checks.az_stor_017

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.encryption.keySource == "Microsoft.Storage"
	msg := sprintf("AZ-STOR-017: Storage account '%s' uses Microsoft-managed encryption keys (properties.encryption.keySource=Microsoft.Storage); customer-managed keys via Key Vault (Microsoft.Keyvault) should be used to enable revocation, rotation, and independent auditing of encryption keys.", [resource.name])
}
