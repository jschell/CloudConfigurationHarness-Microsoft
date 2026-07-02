resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln014'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    defaultToOAuthAuthentication: false
  }
}
