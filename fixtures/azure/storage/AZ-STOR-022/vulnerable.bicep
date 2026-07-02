resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvulnpublicnet001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}
