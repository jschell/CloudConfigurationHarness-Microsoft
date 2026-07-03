resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-purge-protection'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enablePurgeProtection: true
  }
}
