resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stvulnerable001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}
