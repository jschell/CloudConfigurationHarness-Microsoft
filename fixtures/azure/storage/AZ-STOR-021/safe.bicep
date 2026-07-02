resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor021safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    immutableStorageWithVersioning: {
      enabled: true
      immutabilityPolicy: {
        immutabilityPeriodSinceCreationInDays: 30
      }
    }
  }
}
