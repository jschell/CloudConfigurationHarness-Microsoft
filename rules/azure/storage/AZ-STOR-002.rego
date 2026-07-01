package main

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.networkAcls.bypass == "AzureServices"
	msg := "Storage account network ACL bypass is set to AzureServices, allowing trusted Azure platform services to bypass configured network rules even when defaultAction is Deny. Set properties.networkAcls.bypass to 'None' to remove this implicit trust exception."
}
