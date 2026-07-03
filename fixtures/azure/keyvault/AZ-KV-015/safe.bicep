resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-pec-approved'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '11111111-1111-1111-1111-111111111111'
    privateEndpointConnections: [
      {
        name: 'pec-approved'
        properties: {
          privateLinkServiceConnectionState: {
            status: 'Approved'
            description: 'approved'
            actionsRequired: 'None'
          }
        }
      }
    ]
  }
}
