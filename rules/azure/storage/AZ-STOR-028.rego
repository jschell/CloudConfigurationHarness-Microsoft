package checks.az_stor_028

deny contains msg if {
  some resource in input.resources
  resource.type == "Microsoft.Storage/storageAccounts"
  resource.properties.isLocalUserEnabled == true
  msg := "Storage account has local user authentication enabled, which adds a non-AAD credential pathway (password/SSH-key backed) that broadens the auth surface. Disable isLocalUserEnabled when not in use to reduce blast radius."
}
