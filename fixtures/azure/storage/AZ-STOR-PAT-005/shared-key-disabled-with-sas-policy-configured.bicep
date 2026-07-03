resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stsknokeylog005'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: false
    sasPolicy: {
      sasExpirationPeriod: '1.00:00:00'
      expirationAction: 'Log'
    }
  }
}
