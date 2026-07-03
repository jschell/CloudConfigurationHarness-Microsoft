package checks.az_stor_pat_001

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.allowBlobPublicAccess == true
	resource.properties.networkAcls.defaultAction == "Allow"
	msg := "Storage account allows anonymous blob public access while the network ACL default action is Allow, letting any unauthenticated host on the internet read blob data with no credential at all."
}
