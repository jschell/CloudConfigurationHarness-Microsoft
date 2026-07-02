package checks.az_stor_023

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	not oauth_is_default(resource.properties)
	msg := "AZ-STOR-014: Storage account has properties.defaultToOAuthAuthentication set to false (or unset), so the default authentication falls back to Shared Key / SAS semantics rather than Entra ID (Azure AD), weakening per-identity authorization, RBAC enforcement, and audit attribution."
}

oauth_is_default(props) if {
	props.defaultToOAuthAuthentication == true
}
