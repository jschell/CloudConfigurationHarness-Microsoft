resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stlocaluservuln001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isLocalUserEnabled: true
  }
}