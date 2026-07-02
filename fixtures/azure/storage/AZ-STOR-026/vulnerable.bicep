resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvulnerableimmutability'
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
        allowProtectedAppendWrites: true
        periodSinceCreationInDays: 30
      }
    }
  }
}