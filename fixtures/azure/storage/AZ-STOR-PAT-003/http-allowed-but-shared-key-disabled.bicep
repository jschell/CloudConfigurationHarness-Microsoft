resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'sthttpnokeypat003'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: false
    allowSharedKeyAccess: false
  }
}
