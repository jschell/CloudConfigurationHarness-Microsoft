resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stsafe001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    privateEndpointConnections: [
      {
        name: 'pec-001'
        properties: {
          privateEndpoint: {
            id: '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-privatelink/providers/Microsoft.Network/privateEndpoints/pe-sa-001'
          }
          privateLinkServiceConnectionState: {
            status: 'Approved'
            description: 'Auto-approved private endpoint connection'
            actionsRequired: 'None'
          }
        }
      }
    ]
  }
}