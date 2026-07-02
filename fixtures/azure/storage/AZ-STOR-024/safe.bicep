resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor014safe'
  location: 'eastus'
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    immutableStorageWithVersioning: {
      enabled: true
    }
  }
}
