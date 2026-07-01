param location string = 'eastus'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln004'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_0'
  }
}
