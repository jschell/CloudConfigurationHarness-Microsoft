package checks.az_stor_040

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.sasPolicy.expirationAction == "Log"
    msg := "Storage account sasPolicy.expirationAction is set to 'Log', which only audits overlong-lived SAS tokens instead of blocking them, leaving expired shared-access credentials functional"
}
