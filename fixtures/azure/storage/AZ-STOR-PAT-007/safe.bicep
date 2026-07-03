resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpat7safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}
