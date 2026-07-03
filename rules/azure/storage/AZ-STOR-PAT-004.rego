package checks.az_stor_pat_004

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.isSftpEnabled == true
    resource.properties.isLocalUserEnabled == true
    msg := "Storage account exposes an SFTP endpoint authenticated only by local users, creating a live SSH/password-based network surface entirely outside Entra ID RBAC, conditional access, and per-identity auditing."
}
