resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stzstor035safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    networkAcls: {
      defaultAction: 'Deny'
      resourceAccessRules: [
        {
          tenantId: '72f988bf-86f1-41af-91ab-2d7cd011db47'
          resourceId: '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/primary-rg/providers/Microsoft.Network/virtualNetworks/primary-vnet'
        }
      ]
    }
  }
}