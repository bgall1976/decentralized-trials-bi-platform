@description('Databricks workspace. Premium SKU is required (Standard is deprecated as of 2025); cost is controlled by keeping clusters small + auto-terminating.')
param location string
param namePrefix string
param tags object

resource dbw 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: '${namePrefix}-dbw'
  location: location
  tags: tags
  sku: { name: 'premium' }
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', '${namePrefix}-dbw-managed')
  }
}

output workspaceUrl string = dbw.properties.workspaceUrl
