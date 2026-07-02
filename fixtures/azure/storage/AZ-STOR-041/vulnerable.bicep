resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storagedangerous001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    sasPolicy: {
      sasExpirationPeriod: '365.00:00:00'
    }
  }
}