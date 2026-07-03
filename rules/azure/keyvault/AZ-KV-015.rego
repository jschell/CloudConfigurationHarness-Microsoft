package checks.az_kv_015

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    some conn in resource.properties.privateEndpointConnections
    status := conn.properties.privateLinkServiceConnectionState.status
    status != "Approved"
    msg := sprintf("Key Vault '%s' has a privateEndpointConnection whose privateLinkServiceConnectionState.status is '%s'; only 'Approved' establishes an active private-link path to the vault, the secure posture per 'Azure Key Vaults should use private link'. Approve intended private endpoint connections (and reject/remove unintended ones explicitly).", [resource.name, status])
}
