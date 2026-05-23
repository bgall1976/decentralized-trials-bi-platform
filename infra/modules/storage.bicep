@description('ADLS Gen2 (hierarchical namespace) + a landing container. Standard LRS to control cost.')
param location string
param namePrefix string
param suffix string
param tags object

resource sa 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${namePrefix}sa${suffix}')
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true            // ADLS Gen2
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: sa
  name: 'default'
}

resource landing 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blob
  name: 'landing'
}

output storageAccountName string = sa.name
