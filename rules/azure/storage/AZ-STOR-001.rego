package main

deny[msg] {
	input.type == "Microsoft.Storage/storageAccounts"
	input.properties.networkAcls.defaultAction == "Allow"
	msg := "Storage account network ACL default action is set to Allow, permitting access from any network by default. Set properties.networkAcls.defaultAction to 'Deny' and allow only trusted networks."
}
