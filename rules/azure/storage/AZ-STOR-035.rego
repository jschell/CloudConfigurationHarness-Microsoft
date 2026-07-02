package checks.az_stor_035

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	rule := resource.properties.networkAcls.resourceAccessRules[_]
	rule.tenantId != "72f988bf-86f1-41af-91ab-2d7cd011db47"
	msg := sprintf("storage account '%s' networkAcls.resourceAccessRules grants access to a tenantId that is not the account's home tenant; cross-tenant resource access widens the trust boundary", [resource.name])
}
