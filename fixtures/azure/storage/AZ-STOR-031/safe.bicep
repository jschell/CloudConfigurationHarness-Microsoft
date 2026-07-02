resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storsafe001'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    keyPolicy: {
      keyExpirationPeriodInDays: 90
    }
  }
}
