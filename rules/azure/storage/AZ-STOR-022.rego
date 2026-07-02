package checks.az_stor_022

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.publicNetworkAccess == "Enabled"
	msg := "Storage account is reachable over the public internet; set properties.publicNetworkAccess to 'Disabled' to restrict access to private endpoints only."
}
