resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'stskvulnpat005'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: true
    sasPolicy: {
      sasExpirationPeriod: '1.00:00:00'
      expirationAction: 'Log'
    }
  }
}
