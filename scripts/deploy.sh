#!/usr/bin/env bash
# Deploy the platform to the CURRENTLY SELECTED Azure subscription (subscription-scoped Bicep).
# Prereqs: az CLI logged in (`az login`) and subscription selected (`az account set --subscription <ID>`).
set -euo pipefail

LOCATION="${AZURE_LOCATION:-eastus}"
PARAM_FILE="infra/main.parameters.bicepparam"

if [[ ! -f "$PARAM_FILE" ]]; then
  echo "ERROR: $PARAM_FILE not found. Copy infra/main.parameters.example.bicepparam and fill it in."
  exit 1
fi

SUB_ID="$(az account show --query id -o tsv)"
SUB_NAME="$(az account show --query name -o tsv)"
OBJECT_ID="$(az ad signed-in-user show --query id -o tsv)"
echo "Deploying to subscription: $SUB_NAME ($SUB_ID) in $LOCATION"
read -r -p "Proceed? [y/N] " ok; [[ "$ok" == "y" || "$ok" == "Y" ]] || exit 1

# Validate first, then deploy. adminObjectId is injected from the signed-in user (overrides the file).
az deployment sub validate \
  --location "$LOCATION" \
  --template-file infra/main.bicep \
  --parameters "$PARAM_FILE" \
  --parameters adminObjectId="$OBJECT_ID"

az deployment sub create \
  --name dtbi-deploy \
  --location "$LOCATION" \
  --template-file infra/main.bicep \
  --parameters "$PARAM_FILE" \
  --parameters adminObjectId="$OBJECT_ID"

echo "Deploy complete. Run ./scripts/post_deploy.sh next."
