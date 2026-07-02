package checks.az_stor_030

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.isSftpEnabled == true
    msg := "Storage account has SFTP enabled, exposing an additional authentication-capable network surface (local users with SSH keys/passwords) that broadens the data and credential attack surface."
}
