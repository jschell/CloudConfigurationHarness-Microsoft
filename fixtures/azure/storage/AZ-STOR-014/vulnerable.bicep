resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stlogimmutabledeny001'
  location: 'eastus'
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    immutableStorageWithVersioning: {
      enabled: true
      immutabilityPolicy: {
        allowProtectedAppendWrites: false
        state: 'Unlocked'
        periodSinceCreationInDays: 30
      }
    }
  }
}
