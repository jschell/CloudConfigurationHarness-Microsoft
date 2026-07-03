resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-softdelete-full-retention'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '00000000-0000-0000-0000-000000000000'
    softDeleteRetentionInDays: 90
  }
}
