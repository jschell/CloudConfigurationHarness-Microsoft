resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storsafesftp001'
  location: 'eastus'
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    isSftpEnabled: false
  }
}