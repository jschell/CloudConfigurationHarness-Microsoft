package checks.az_stor_pat_005

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.allowSharedKeyAccess == true
    resource.properties.sasPolicy.expirationAction == "Log"
    msg := "Storage account allows Shared Key access while sasPolicy.expirationAction is 'Log' (audit-only), so account-key-signed SAS tokens can outlive their intended lifetime with no enforcement and no central way to revoke them short of rolling the account key."
}
