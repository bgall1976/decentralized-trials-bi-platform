@description('Key Vault for secrets (e.g. Databricks PAT). RBAC-authorized; no secrets in git.')
param location string
param namePrefix string
param suffix string
param adminObjectId string
param tags object

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: toLower('${namePrefix}-kv-${substring(suffix, 0, 6)}')
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// Grant the deploying admin Key Vault Secrets Officer.
resource kvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, adminObjectId, 'kv-secrets-officer')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
    principalId: adminObjectId
  }
}

output keyVaultName string = kv.name
