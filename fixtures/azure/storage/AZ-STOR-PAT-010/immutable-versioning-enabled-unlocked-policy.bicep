resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpat10unlocked'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    immutableStorageWithVersioning: {
      enabled: true
      immutabilityPolicy: {
        state: 'Unlocked'
      }
    }
  }
}
