resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stsafehns001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: false
  }
}