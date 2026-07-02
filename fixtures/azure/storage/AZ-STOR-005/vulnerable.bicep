resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln005'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: true
  }
}
