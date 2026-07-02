resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stzstor020safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      services: {
        queue: {
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}
