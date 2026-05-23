@description('Databricks workspace. Standard SKU keeps cost down for a demo; cluster auto-terminates.')
param location string
param namePrefix string
param tags object

resource dbw 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: '${namePrefix}-dbw'
  location: location
  tags: tags
  sku: { name: 'standard' }
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', '${namePrefix}-dbw-managed')
  }
}

output workspaceUrl string = dbw.properties.workspaceUrl
