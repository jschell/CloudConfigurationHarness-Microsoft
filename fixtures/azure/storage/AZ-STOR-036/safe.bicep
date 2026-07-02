resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stsafe036'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      virtualNetworkRules: [
        {
          id: '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-net/providers/Microsoft.Network/subnets/snet-storage'
          action: 'Allow'
        }
      ]
    }
  }
}