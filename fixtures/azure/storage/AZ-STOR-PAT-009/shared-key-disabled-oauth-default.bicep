resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpat9safekeyoauth'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
  }
}
