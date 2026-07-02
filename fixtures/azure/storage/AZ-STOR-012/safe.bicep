resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stazstor012safe'
  location: 'eastus'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    azureFilesIdentityBasedAuthentication: {
      directoryServiceOptions: 'AADDS'
    }
  }
}
