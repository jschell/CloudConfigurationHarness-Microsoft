package checks.az_stor_013

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	settings := resource.properties.azureFilesIdentityBasedAuthentication.smbOAuthSettings
	not is_smb_oauth_enabled(settings)
	msg := "AZ-STOR-013: Storage account has properties.azureFilesIdentityBasedAuthentication.smbOAuthSettings.isSmbOAuthEnabled disabled (false); managed identities cannot use OAuth (Entra ID) for SMB share access, forcing reliance on storage account shared keys."
}

is_smb_oauth_enabled(settings) if {
	settings.isSmbOAuthEnabled == true
}

is_smb_oauth_enabled(settings) if {
	settings.isSmbOAuthEnabled == 1
}
