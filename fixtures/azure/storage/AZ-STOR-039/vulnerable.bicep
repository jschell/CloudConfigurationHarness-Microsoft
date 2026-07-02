resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvulnrouting001'
  location: 'eastus'
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    routingPreference: {
      routingChoice: 'InternetRouting'
    }
  }
}
