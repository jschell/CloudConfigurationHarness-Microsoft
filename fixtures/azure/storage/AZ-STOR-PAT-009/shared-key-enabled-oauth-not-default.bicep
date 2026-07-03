resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpat9vulnkeyoauth'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: true
    defaultToOAuthAuthentication: false
  }
}
