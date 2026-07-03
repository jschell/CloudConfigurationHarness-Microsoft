resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsksafepat005'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: false
  }
}
