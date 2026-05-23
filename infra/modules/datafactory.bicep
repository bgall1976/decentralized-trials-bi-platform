@description('Azure Data Factory with a system-assigned identity for managed-identity access to ADLS/Key Vault.')
param location string
param namePrefix string
param storageAccountName string
param tags object

resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: '${namePrefix}-adf'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
}

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Give ADF's managed identity Storage Blob Data Contributor on the lake (no keys in linked services).
resource adfStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: sa
  name: guid(sa.id, adf.id, 'blob-data-contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: adf.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output dataFactoryName string = adf.name
