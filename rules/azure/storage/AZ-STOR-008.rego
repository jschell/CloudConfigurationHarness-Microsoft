package checks.az_stor_008

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.allowCrossTenantReplication == true
	msg := "AZ-STOR-008: Storage account permits cross-tenant object replication; set allowCrossTenantReplication to false to restrict replication to the home AAD tenant."
}
