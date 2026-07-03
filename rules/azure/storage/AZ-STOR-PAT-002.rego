package checks.az_stor_pat_002

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.isNfsV3Enabled == true
	resource.properties.networkAcls.defaultAction == "Allow"
	msg := "Storage account has NFSv3 enabled while the network ACL default action is Allow, exposing an unauthenticated network filesystem that any host on the internet can mount and read with no credential whatsoever."
}
