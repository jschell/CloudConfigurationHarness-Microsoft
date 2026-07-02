resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stornfsv3vulnerable001'
  location: 'eastus'
  sku: {
    name: 'Premium_LRS'
  }
  kind: 'BlockBlobStorage'
  properties: {
    isNfsV3Enabled: true
    largeFileSharesState: 'Enabled'
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}