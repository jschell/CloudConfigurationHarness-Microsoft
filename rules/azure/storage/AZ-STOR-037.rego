package checks.az_stor_037

import rego.v1

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	connections := object.get(resource.properties, "privateEndpointConnections", [])
	count(connections) > 0
	some conn in connections
	state := object.get(conn.properties.privateLinkServiceConnectionState, "status", "")
	state != "Approved"
	name := object.get(resource, "name", "<storage account>")
	msg := sprintf("%s: storage account private endpoint connection is not Approved (status='%s'); approve private-link connections to enforce private-only access", [name, state])
}

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	not has_private_endpoint_connection(resource)
	name := object.get(resource, "name", "<storage account>")
	msg := sprintf("%s: storage account has no private endpoint connections; configure and approve at least one private endpoint to enforce private-only access", [name])
}

has_private_endpoint_connection(resource) if {
	connections := object.get(resource.properties, "privateEndpointConnections", [])
	count(connections) > 0
}