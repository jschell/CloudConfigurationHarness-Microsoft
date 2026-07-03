package checks.az_kv_009

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.enabledForTemplateDeployment == true
    msg := sprintf("Key Vault '%s' has enabledForTemplateDeployment enabled; set properties.enabledForTemplateDeployment to false so that Azure Resource Manager cannot retrieve secrets from the vault during template deployments", [resource.name])
}
