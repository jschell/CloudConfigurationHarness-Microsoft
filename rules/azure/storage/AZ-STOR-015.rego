package checks.az_stor_015

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.encryption.identity.userAssignedIdentity == ""
	msg := "properties.encryption.identity.federatedIdentityClientId should not be empty"
}
