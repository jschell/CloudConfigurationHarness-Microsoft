resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsftpsafepat004'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    isSftpEnabled: false
    isLocalUserEnabled: false
  }
}
