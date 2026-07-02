package checks.az_stor_034

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	not resource.properties.networkAcls.ipv6Rules == null
	some rule in resource.properties.networkAcls.ipv6Rules
	rule.value == "::/0"
	msg := sprintf("storage account '%s' networkAcls.ipv6Rules contains '::/0', exposing the account to the entire IPv6 internet", [resource.name])
}
