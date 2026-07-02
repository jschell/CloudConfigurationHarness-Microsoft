package checks.az_stor_031

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    keypol := resource.properties.keyPolicy
    not keypol.keyExpirationPeriodInDays >= 90
    msg := "Storage account keyPolicy.keyExpirationPeriodInDays is less than 90 days (or absent), permitting long-lived Shared Key credentials that widen the exposure window if a key leaks."
}
