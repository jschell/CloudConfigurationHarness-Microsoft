param location string = 'eastus'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stsafe003'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
  }
}
