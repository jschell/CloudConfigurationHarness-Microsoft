resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'storaclsafe033'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      ipv6Rules: [
        {
          value: 'fd00:db8::/64'
          action: 'Allow'
        }
      ]
    }
  }
}
