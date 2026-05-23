using './main.bicep'

// Copy to main.parameters.bicepparam and fill in. This file is the only place env values live.
// The Subscription ID is NOT set here — it is selected at deploy time via:
//   az account set --subscription "<YOUR_SUBSCRIPTION_ID>"

param location = 'eastus'
param resourcePrefix = 'dtbi'
param adminObjectId = '<YOUR_AAD_OBJECT_ID>'   // az ad signed-in-user show --query id -o tsv
param tags = {
  project: 'decentralized-trials-bi-platform'
  managedBy: 'bicep'
  costCenter: 'demo'
}
