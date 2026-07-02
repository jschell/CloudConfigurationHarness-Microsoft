package checks.az_stor_011

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.azureFilesIdentityBasedAuthentication.defaultSharePermission == "StorageFileDataSmbShareElevatedContributor"
	msg := "Storage account default SMB share permission is set to StorageFileDataSmbShareElevatedContributor, granting elevated file-share access as a fallback to Kerberos-authenticated users without an explicit RBAC role assignment."
}
