resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stvulnerable002'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}
