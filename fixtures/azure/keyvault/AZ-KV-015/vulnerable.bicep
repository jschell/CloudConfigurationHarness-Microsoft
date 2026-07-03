resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-pec-rejected'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '11111111-1111-1111-1111-111111111111'
    privateEndpointConnections: [
      {
        name: 'pec-rejected'
        properties: {
          privateLinkServiceConnectionState: {
            status: 'Rejected'
            description: 'rejected'
            actionsRequired: 'None'
          }
        }
      }
    ]
  }
}
