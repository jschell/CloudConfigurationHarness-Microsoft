resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storaclrisk032'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: [
        {
          value: '0.0.0.0/0'
          action: 'Allow'
        }
      ]
    }
  }
}
