#!/usr/bin/env bash
# Delete everything so nothing keeps billing. Targets the resource group created by main.bicep.
set -euo pipefail
PREFIX="${RESOURCE_PREFIX:-dtbi}"
RG="${PREFIX}-rg"
echo "This will DELETE resource group '$RG' and all resources in it (subscription: $(az account show --query name -o tsv))."
read -r -p "Type the resource group name to confirm: " confirm
[[ "$confirm" == "$RG" ]] || { echo "Aborted."; exit 1; }
az group delete --name "$RG" --yes --no-wait
echo "Deletion started for $RG. Verify in the portal that the Databricks managed RG is also removed."
