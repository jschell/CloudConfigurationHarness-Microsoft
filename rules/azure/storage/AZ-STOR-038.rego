package checks.az_stor_038

deny contains msg if {
  some resource in input.resources
  resource.type == "Microsoft.Storage/storageAccounts"
  resource.properties.routingPreference.publishInternetEndpoints != false
  msg := "Storage account routingPreference.publishInternetEndpoints is not explicitly disabled, exposing the account over the public internet routing path"
}
