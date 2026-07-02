resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stzstor035vuln'
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
          tenantId: '11111111-2222-3333-4444-555555555555'
          resourceId: '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/other-rg/providers/Microsoft.Network/virtualNetworks/other-vnet'
        }
      ]
    }
  }
}