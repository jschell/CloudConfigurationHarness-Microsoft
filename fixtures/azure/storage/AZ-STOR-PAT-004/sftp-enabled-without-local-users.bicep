resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsftpnolusrpat004'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    isSftpEnabled: true
    isLocalUserEnabled: false
  }
}
