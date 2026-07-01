resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsafe002'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}
