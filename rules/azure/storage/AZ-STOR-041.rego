package checks.az_stor_041

import rego.v1

deny contains msg if {
	some resource in input.resources
	resource.type == "Microsoft.Storage/storageAccounts"
	resource.properties.sasPolicy.sasExpirationPeriod == "365.00:00:00"
	msg := "Storage account SAS expiration period is set to 365 days (properties.sasPolicy.sasExpirationPeriod == '365.00:00:00'), permitting long-lived shared access signatures; reduce to a short lifetime (e.g. '1.00:00:00') to bound credential-exposure risk"
}
