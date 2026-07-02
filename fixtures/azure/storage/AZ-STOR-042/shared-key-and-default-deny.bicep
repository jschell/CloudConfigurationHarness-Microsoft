resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'sharedkeydefaultdeny'
  location: 'eastus'
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: true
    networkAcls: {
      defaultAction: 'Deny'
    }
  }
}