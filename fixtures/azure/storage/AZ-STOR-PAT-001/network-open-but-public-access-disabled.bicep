resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stnetopennopub001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}
