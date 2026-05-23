#!/usr/bin/env bash
# Post-deploy wiring: push synthetic data to the lake and store the Databricks PAT in Key Vault.
set -euo pipefail

OUT="$(az deployment sub show --name dtbi-deploy --query properties.outputs -o json)"
STORAGE="$(echo "$OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["storageAccount"]["value"])')"
KV="$(echo "$OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["keyVaultName"]["value"])')"

echo "Generating synthetic data locally..."
python3 -m src.generators.generate_all

echo "Uploading synthetic extracts to landing container in $STORAGE ..."
az storage blob upload-batch \
  --account-name "$STORAGE" --auth-mode login \
  --destination landing --source data/landing --pattern "*.csv" --overwrite

if [[ -n "${DATABRICKS_PAT:-}" ]]; then
  echo "Storing Databricks PAT in Key Vault $KV ..."
  az keyvault secret set --vault-name "$KV" --name databricks-pat --value "$DATABRICKS_PAT" >/dev/null
else
  echo "NOTE: set DATABRICKS_PAT env var and re-run to store the Databricks token in Key Vault,"
  echo "      or add it manually:  az keyvault secret set --vault-name $KV --name databricks-pat --value <PAT>"
fi

echo "Post-deploy complete. Import adf/ artifacts and run pipeline pl_ingest_and_transform."
