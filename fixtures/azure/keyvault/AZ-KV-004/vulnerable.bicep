resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-all-key'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: '11111111-1111-1111-1111-111111111111'
        permissions: {
          keys: [
            'all'
          ]
        }
      }
    ]
  }
}
