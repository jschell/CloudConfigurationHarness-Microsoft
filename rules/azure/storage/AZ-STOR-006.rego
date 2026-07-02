package checks.az_stor_006

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.allowSharedKeyAccess == true
	msg := "AZ-STOR-006: Storage account allows Shared Key access; disable allowSharedKeyAccess to force Entra ID (Azure AD) authorization."
}
