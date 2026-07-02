package checks.az_stor_010

deny contains msg if {
    some resource in input.resources
    resource.type == "Microsoft.Storage/storageAccounts"
    resource.properties.dualStackEndpointPreference.publishIpv6Endpoint == true
    msg := "Storage account publishes an IPv6 public endpoint (dualStackEndpointPreference.publishIpv6Endpoint is true), widening the public network attack surface"
}
