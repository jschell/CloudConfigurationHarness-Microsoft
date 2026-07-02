resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln038'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    routingPreference: {
      publishInternetEndpoints: true
    }
  }
}