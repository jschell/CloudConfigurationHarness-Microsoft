package checks.az_kv_007

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.KeyVault/vaults"
    resource.properties.enableRbacAuthorization == false
    msg := sprintf("Key Vault '%s' uses legacy vault access policies (enableRbacAuthorization is false); set properties.enableRbacAuthorization to true to use the centralized, auditable RBAC permission model", [resource.name])
}
