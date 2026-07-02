resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storaclz015safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      identity: {
        userAssignedIdentity: '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-kv/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-encryption'
      }
    }
  }
}
