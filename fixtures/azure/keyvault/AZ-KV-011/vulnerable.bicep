resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-vulnerable'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: '11111111-1111-1111-1111-111111111111'
    enabledForTemplateDeployment: true
  }
}
