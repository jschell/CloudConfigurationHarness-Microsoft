resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln009'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowedCopyScope: 'PrivateLink'
  }
}