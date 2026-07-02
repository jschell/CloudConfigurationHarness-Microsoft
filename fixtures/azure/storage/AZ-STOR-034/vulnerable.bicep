resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stvuln034'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipv6Rules: [
        {
          value: '::/0'
          action: 'Allow'
        }
      ]
    }
  }
}