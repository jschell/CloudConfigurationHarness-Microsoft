resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storaclz015vuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      identity: {
        userAssignedIdentity: ''
      }
    }
  }
}
