resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storaclsafe032'
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
          value: '10.0.0.0/24'
          action: 'Allow'
        }
      ]
    }
  }
}
