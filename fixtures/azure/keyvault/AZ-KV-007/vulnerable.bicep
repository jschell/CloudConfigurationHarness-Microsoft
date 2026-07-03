resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-legacy-access-policies'
  location: 'eastus'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: false
  }
}
