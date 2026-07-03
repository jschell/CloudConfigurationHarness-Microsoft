resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-template-deploy-disabled'
  location: 'eastus'
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enabledForTemplateDeployment: false
  }
}
