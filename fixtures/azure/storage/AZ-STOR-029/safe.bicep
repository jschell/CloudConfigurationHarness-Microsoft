resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stornfsv3safe001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    isNfsV3Enabled: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}