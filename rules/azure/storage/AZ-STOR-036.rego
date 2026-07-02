package checks.az_stor_036

import rego.v1

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	rule_set := object.get(resource.properties.networkAcls, "virtualNetworkRules", [])
	count(rule_set) == 0
	resource.properties.networkAcls.defaultAction == "Deny"
	msg := "Storage account networkAcls.defaultAction=Deny but virtualNetworkRules is missing, null, or empty; virtualNetworkRules[].id should reference a specific dedicated subnet id"
}

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	some rule in object.get(resource.properties.networkAcls, "virtualNetworkRules", [])
	not object.get(rule, "id", null)
	resource.properties.networkAcls.defaultAction == "Deny"
	msg := "Storage account virtualNetworkRules entry has a null/missing id; each rule should reference a specific dedicated subnet id"
}
