resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsftpvulnpat004'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    isSftpEnabled: true
    isLocalUserEnabled: true
  }
}
