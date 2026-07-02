resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor006vuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: true
  }
}
