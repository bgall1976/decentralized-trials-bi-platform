// Subscription-scoped deployment: creates the resource group and all platform resources in one
// `az deployment sub create`. Subscription is selected at deploy time via `az account set`.
targetScope = 'subscription'

@description('Azure region for all resources.')
param location string = 'eastus'

@description('Short prefix for resource names (lowercase, 3-8 chars).')
@minLength(3)
@maxLength(8)
param resourcePrefix string = 'dtbi'

@description('Object ID of the deploying user/SP, granted Key Vault access.')
param adminObjectId string

@description('Tags applied to every resource.')
param tags object = {
  project: 'decentralized-trials-bi-platform'
  managedBy: 'bicep'
  costCenter: 'demo'
}

var suffix = uniqueString(subscription().subscriptionId, resourcePrefix)
var rgName = '${resourcePrefix}-rg'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage'
  params: { location: location, namePrefix: resourcePrefix, suffix: suffix, tags: tags }
}

module keyvault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyvault'
  params: { location: location, namePrefix: resourcePrefix, suffix: suffix, adminObjectId: adminObjectId, tags: tags }
}

module databricks 'modules/databricks.bicep' = {
  scope: rg
  name: 'databricks'
  params: { location: location, namePrefix: resourcePrefix, tags: tags }
}

module adf 'modules/datafactory.bicep' = {
  scope: rg
  name: 'datafactory'
  params: { location: location, namePrefix: resourcePrefix, storageAccountName: storage.outputs.storageAccountName, tags: tags }
}

output resourceGroup string = rg.name
output storageAccount string = storage.outputs.storageAccountName
output keyVaultName string = keyvault.outputs.keyVaultName
output dataFactoryName string = adf.outputs.dataFactoryName
output databricksWorkspaceUrl string = databricks.outputs.workspaceUrl
