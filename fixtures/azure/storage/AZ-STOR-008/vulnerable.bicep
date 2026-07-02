resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor008vuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowCrossTenantReplication: true
  }
}
