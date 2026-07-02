resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor016safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/rg-cmk/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-cmk': {}
    }
  }
  properties: {
    encryption: {
      services: {
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Keyvault'
      identity: {
        userAssignedIdentity: '/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/rg-cmk/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uami-cmk'
      }
    }
  }
}
