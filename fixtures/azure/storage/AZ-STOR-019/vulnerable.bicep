resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor019vuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      services: {
        file: {
          keyType: 'Service'
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}