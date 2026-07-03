resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stnfsrestrictpat002'
  location: 'eastus'
  sku: {
    name: 'Premium_LRS'
  }
  kind: 'BlockBlobStorage'
  properties: {
    isHnsEnabled: true
    isNfsV3Enabled: true
    supportsHttpsTrafficOnly: false
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}
