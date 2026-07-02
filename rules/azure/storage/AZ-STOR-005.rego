package checks.az_stor_005

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.allowBlobPublicAccess == true
	msg := "Storage account allows anonymous public blob access; set properties.allowBlobPublicAccess to false to prohibit containers from being configured for public read access."
}
