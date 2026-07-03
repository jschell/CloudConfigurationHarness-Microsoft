package checks.az_stor_pat_008

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.allowSharedKeyAccess == true
    keypol := object.get(resource.properties, "keyPolicy", {})
    days := object.get(keypol, "keyExpirationPeriodInDays", 0)
    days < 90
    msg := sprintf("Storage account allows Shared Key access while keyPolicy.keyExpirationPeriodInDays is %v (absent or below the 90-day minimum), so the long-lived, unattributable account key is permitted and is never forced to rotate on an adequate cadence -- a single leak grants indefinite, full-control account takeover with no built-in remediation window.", [days])
}
