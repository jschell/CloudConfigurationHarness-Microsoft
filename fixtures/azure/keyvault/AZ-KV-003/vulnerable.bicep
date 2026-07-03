resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-vulnerable'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '00000000-0000-0000-0000-000000000000'
    accessPolicies: [
      {
        tenantId: '00000000-0000-0000-0000-000000000000'
        objectId: '00000000-0000-0000-0000-000000000000'
        permissions: {
          keys: [
            'all'
          ]
        }
      }
    ]
  }
}
