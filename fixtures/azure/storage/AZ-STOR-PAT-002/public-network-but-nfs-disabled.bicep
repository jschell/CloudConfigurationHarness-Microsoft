resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stpubnfsoffpat002'
  location: 'eastus'
  sku: {
    name: 'Premium_LRS'
  }
  kind: 'BlockBlobStorage'
  properties: {
    isHnsEnabled: true
    isNfsV3Enabled: false
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}
