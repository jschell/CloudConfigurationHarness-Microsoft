package checks.az_stor_009

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.allowedCopyScope == "PrivateLink"
	msg := "AZ-STOR-009: Storage account allowedCopyScope is set to PrivateLink; set allowedCopyScope to AAD to constrain copy operations to the AAD tenant boundary."
}
