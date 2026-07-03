resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stvulnpat001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: true
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}
