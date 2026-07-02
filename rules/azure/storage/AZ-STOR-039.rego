package checks.az_stor_039

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.routingPreference.routingChoice == "InternetRouting"
    msg := "storage account routingPreference.routingChoice is set to InternetRouting, exposing traffic over the public internet instead of the Microsoft backbone"
}
