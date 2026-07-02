package checks.az_stor_012

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.azureFilesIdentityBasedAuthentication.directoryServiceOptions == "None"
	msg := "Storage account azureFilesIdentityBasedAuthentication.directoryServiceOptions is set to None, leaving identity-based authentication disabled and forcing SMB share access to fall back to storage keys or anonymous access, weakening per-identity access control."
}
