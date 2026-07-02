package checks.az_stor_027

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.isHnsEnabled == true
	msg := "Storage account has Hierarchical Namespace (HNS) enabled, transforming it into a Data Lake Storage Gen2 account and broadening the attack surface (ACL/POSIX model, SFTP/NFSv3 gating)"
}
