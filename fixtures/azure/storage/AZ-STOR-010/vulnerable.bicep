resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stordualstackvuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    dualStackEndpointPreference: {
      publishIpv6Endpoint: true
    }
  }
}