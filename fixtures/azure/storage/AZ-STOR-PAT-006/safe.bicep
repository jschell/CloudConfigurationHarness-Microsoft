resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsftpnetsafepat6'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true
    isSftpEnabled: false
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}
