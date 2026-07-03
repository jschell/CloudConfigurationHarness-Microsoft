package checks.az_stor_pat_006

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.isSftpEnabled == true
	resource.properties.networkAcls.defaultAction == "Allow"
	msg := "Storage account has SFTP enabled while the network ACL default action is Allow, exposing a public SFTP endpoint backed by long-lived local credentials that can be password-sprayed or brute-forced from anywhere on the internet with no Entra conditional access or per-identity auditing in front of it."
}
