package checks.az_stor_014

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.immutableStorageWithVersioning.immutabilityPolicy.allowProtectedAppendWrites == false
	msg := "properties.immutableStorageWithVersioning.immutabilityPolicy.allowProtectedAppendWrites should be true to preserve write-once semantics for append-blob log workloads under immutability protection"
}
