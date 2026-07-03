resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-test'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '11111111-1111-1111-1111-111111111111'
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: [
        {
          value: '0.0.0.0/0'
        }
      ]
    }
  }
}
