resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor020vuln'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      services: {
        queue: {
          keyType: 'Service'
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}