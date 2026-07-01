# Azure Storage account config sources (pinned)

Pinned excerpts for the `schema_extract` state of
`harness/workflows/storage-atomic-tier.yaml`. Every excerpt below is a
verbatim (or lightly reformatted for length) copy of a JSON node fetched
from the given repo + commit SHA, not a paraphrase. This file gives the
model raw schema and policy-catalog material; it does not name the
attack-path hypothesis to propose -- that is `schema_extract`'s job.

## 1. Storage Resource Manager swagger, `storage.json`

Repo: `Azure/azure-rest-api-specs`
Commit: `f7db5b77f98144ddacf6ce563330ded00f0b71d1`
Path: `specification/storage/resource-manager/Microsoft.Storage/stable/2025-01-01/storage.json`
Full URL: https://raw.githubusercontent.com/Azure/azure-rest-api-specs/f7db5b77f98144ddacf6ce563330ded00f0b71d1/specification/storage/resource-manager/Microsoft.Storage/stable/2025-01-01/storage.json

### `definitions.NetworkRuleSet`

```json
{
  "properties": {
    "bypass": {
      "type": "string",
      "enum": ["None", "Logging", "Metrics", "AzureServices"],
      "default": "AzureServices",
      "description": "Specifies whether traffic is bypassed for Logging/Metrics/AzureServices. Possible values are any combination of Logging|Metrics|AzureServices (For example, \"Logging, Metrics\"), or None to bypass none of those traffics."
    },
    "resourceAccessRules": {
      "type": "array",
      "items": { "$ref": "#/definitions/ResourceAccessRule" },
      "description": "Sets the resource access rules"
    },
    "virtualNetworkRules": {
      "type": "array",
      "items": { "$ref": "#/definitions/VirtualNetworkRule" },
      "description": "Sets the virtual network rules"
    },
    "ipRules": {
      "type": "array",
      "items": { "$ref": "#/definitions/IPRule" },
      "description": "Sets the IP ACL rules"
    },
    "ipv6Rules": {
      "type": "array",
      "items": { "$ref": "#/definitions/IPRule" },
      "description": "Sets the IPv6 ACL rules."
    },
    "defaultAction": {
      "type": "string",
      "enum": ["Allow", "Deny"],
      "default": "Allow",
      "description": "Specifies the default action of allow or deny when no other rules match."
    }
  },
  "required": ["defaultAction"],
  "description": "Network rule set"
}
```

### `definitions.Encryption`

```json
{
  "properties": {
    "services": { "$ref": "#/definitions/EncryptionServices", "description": "List of services which support encryption." },
    "keySource": {
      "type": "string",
      "description": "The encryption keySource (provider). Possible values (case-insensitive):  Microsoft.Storage, Microsoft.Keyvault",
      "enum": ["Microsoft.Storage", "Microsoft.Keyvault"],
      "default": "Microsoft.Storage"
    },
    "requireInfrastructureEncryption": {
      "type": "boolean",
      "description": "A boolean indicating whether or not the service applies a secondary layer of encryption with platform managed keys for data at rest."
    },
    "keyvaultproperties": { "$ref": "#/definitions/KeyVaultProperties", "description": "Properties provided by key vault." },
    "identity": { "$ref": "#/definitions/EncryptionIdentity", "description": "The identity to be used with service-side encryption at rest." }
  },
  "description": "The encryption settings on the storage account."
}
```

### Selected scalar properties of `definitions.StorageAccountProperties`

```json
{
  "supportsHttpsTrafficOnly": {
    "type": "boolean",
    "x-ms-client-name": "EnableHttpsTrafficOnly",
    "description": "Allows https traffic only to storage service if sets to true."
  },
  "networkAcls": {
    "$ref": "#/definitions/NetworkRuleSet",
    "x-ms-client-name": "NetworkRuleSet",
    "description": "Network rule set",
    "readOnly": true
  },
  "allowBlobPublicAccess": {
    "type": "boolean",
    "x-ms-client-name": "AllowBlobPublicAccess",
    "description": "Allow or disallow public access to all blobs or containers in the storage account. The default interpretation is false for this property."
  },
  "minimumTlsVersion": {
    "type": "string",
    "enum": ["TLS1_0", "TLS1_1", "TLS1_2", "TLS1_3"],
    "description": "Set the minimum TLS version to be permitted on requests to storage. The default interpretation is TLS 1.0 for this property. Minimum TLS version 1.3 version is not supported."
  },
  "publicNetworkAccess": {
    "$ref": "#/definitions/PublicNetworkAccess",
    "description": "Allow, disallow, or let Network Security Perimeter configuration to evaluate public network access to Storage Account."
  },
  "allowSharedKeyAccess": {
    "type": "boolean",
    "description": "Indicates whether the storage account permits requests to be authorized with the account access key via Shared Key. If false, then all requests, including shared access signatures, must be authorized with Azure Active Directory (Azure AD). The default value is null, which is equivalent to true."
  },
  "defaultToOAuthAuthentication": {
    "type": "boolean",
    "description": "A boolean flag which indicates whether the default authentication is OAuth or not. The default interpretation is false for this property."
  },
  "isHnsEnabled": {
    "type": "boolean",
    "description": "Account HierarchicalNamespace enabled if sets to true."
  }
}
```

## 2. Azure Policy built-in alias catalog (existing coverage, for `existing_policy_ref`)

Repo: `Azure/azure-policy`
Commit: `d315bc3b9c8a382e540add3562fff4a82e027635`
Path: `built-in-policies/policyDefinitions/Storage/`

Definitions retrieved (displayName + the `policyRule.if` condition, i.e. what
the built-in already audits):

* `Storage_NetworkAcls_Audit.json` -- "Storage accounts should restrict
  network access" --
  `{"allOf": [{"field": "type", "equals": "Microsoft.Storage/storageAccounts"}, {"field": "Microsoft.Storage/storageAccounts/networkAcls.defaultAction", "notEquals": "Deny"}]}`
* `StorageAccountMinimumTLSVersion_Audit.json` -- "Storage accounts should
  have the specified minimum TLS version" --
  `{"allOf": [{"field": "type", "equals": "Microsoft.Storage/storageAccounts"}, {"anyOf": [{"field": "Microsoft.Storage/storageAccounts/minimumTlsVersion", "notEquals": "[parameters('minimumTlsVersion')]"}, {"field": "Microsoft.Storage/storageAccounts/minimumTlsVersion", "exists": "false"}]}]}`
* `Storage_AuditForHTTPSEnabled_Audit.json` -- "Secure transfer to storage
  accounts should be enabled" --
  `{"allOf": [{"field": "type", "equals": "Microsoft.Storage/storageAccounts"}, {"anyOf": [{"allOf": [{"value": "[requestContext().apiVersion]", "less": "2019-04-01"}, {"field": "Microsoft.Storage/storageAccounts/supportsHttpsTrafficOnly", "exists": "false"}]}, {"field": "Microsoft.Storage/storageAccounts/supportsHttpsTrafficOnly", "equals": "false"}]}]}`
* `ASC_Storage_DisallowPublicBlobAccess_Audit.json` -- Microsoft Defender
  for Cloud recommendation covering `allowBlobPublicAccess`.
* `StoragePublicNetworkAccess_AuditDeny.json` /
  `StoragePublicNetworkAccess_Modify.json` -- cover `publicNetworkAccess`.
* `StorageAccountAllowSharedKeyAccess_Audit.json` -- covers
  `allowSharedKeyAccess`.

Full directory listing (`Azure/azure-policy` at the pinned commit,
`built-in-policies/policyDefinitions/Storage/`) is available via:
https://github.com/Azure/azure-policy/tree/d315bc3b9c8a382e540add3562fff4a82e027635/built-in-policies/policyDefinitions/Storage
