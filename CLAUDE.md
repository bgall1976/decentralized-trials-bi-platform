# CLAUDE.md — operating guide for deploying this repo to Azure

You (Claude Code) are deploying this platform to the user's **personal Azure subscription**. This
file is the runbook. Read it fully before running anything. Work through the phases in order, and
**stop and ask the user at every point marked STOP.**

## Non-negotiable rules

1. **Cost.** This is a personal subscription. Never create resources beyond what `infra/` defines,
   never scale up SKUs, never start an always-on/interactive Databricks cluster, and always confirm
   with the user before any `az deployment ... create`. Remind the user to tear down when done.
2. **Secrets.** Never write a Databricks token, connection string, or any secret into a file that
   gets committed. Secrets go only into Azure Key Vault. The real `infra/main.parameters.bicepparam`,
   `.env`, and any token files are gitignored — keep it that way.
3. **Data.** All data here is synthetic. Never introduce real PHI.
4. **Idempotence.** Prefer commands that are safe to re-run. If a step fails, diagnose before retrying.
5. **Don't guess identifiers.** Read subscription/resource names from `az` output, not from memory.

## What you are deploying

Subscription-scoped Bicep creates a resource group plus ADLS Gen2, Key Vault, Azure Data Factory
(system-assigned managed identity), and an Azure Databricks workspace. Then synthetic data is loaded
to the lake and the Databricks medallion (Bronze -> Silver -> Gold) is run to produce the Gold marts
that power the dashboard and Power BI model. Full background: `README.md`, `docs/architecture.md`,
`docs/COST.md`, `docs/HIPAA_NOTES.md`. (For deploying via GitHub Actions OIDC instead of locally,
see `docs/CICD_OIDC.md` — but this runbook covers the local Claude Code path.)

---

## Phase 0 — Preflight

```bash
az version                 # confirm Azure CLI is installed
az account show            # confirm logged in; note the subscription name + id
az ad signed-in-user show --query id -o tsv    # capture this -> ADMIN_OBJECT_ID
az bicep version || az bicep install
```

- **STOP:** Show the user the subscription name/id from `az account show` and confirm it is the
  correct (personal) subscription before continuing. If they need a different one:
  `az account set --subscription "<ID>"`.
- Register resource providers (a fresh subscription often needs these; safe to re-run):

```bash
for ns in Microsoft.Storage Microsoft.KeyVault Microsoft.DataFactory Microsoft.Databricks; do
  az provider register --namespace $ns
done
# poll until all show "Registered" before deploying
az provider show -n Microsoft.Databricks --query registrationState -o tsv
```

## Phase 1 — Provision infrastructure (Bicep)

Set variables (ask the user for prefix/region or use defaults `dtbi` / `eastus`):

```bash
LOCATION=eastus
PREFIX=dtbi
ADMIN_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
```

Lint, then preview, then deploy:

```bash
az bicep build --file infra/main.bicep                      # compile/lint, no Azure calls

az deployment sub what-if \
  --location "$LOCATION" --template-file infra/main.bicep \
  --parameters location="$LOCATION" resourcePrefix="$PREFIX" adminObjectId="$ADMIN_OBJECT_ID"
```

- **STOP:** Show the user the `what-if` output (what will be created) and the note that this starts
  incurring Azure cost. Get explicit approval. Only then:

```bash
az deployment sub create \
  --name dtbi-deploy --location "$LOCATION" --template-file infra/main.bicep \
  --parameters location="$LOCATION" resourcePrefix="$PREFIX" adminObjectId="$ADMIN_OBJECT_ID"
```

> You may instead run `./scripts/deploy.sh`, but it has an interactive prompt and expects
> `infra/main.parameters.bicepparam` to exist; the direct `az` commands above are preferred for an
> automated session. Do NOT pipe `yes` into it to bypass the confirmation.

Capture outputs for later phases:

```bash
az deployment sub show --name dtbi-deploy --query properties.outputs -o json
# -> storageAccount, keyVaultName, dataFactoryName, databricksWorkspaceUrl, resourceGroup
```

## Phase 2 — Verify infrastructure and governance

```bash
RG="${PREFIX}-rg"
az resource list -g "$RG" -o table
```

Confirm: storage account (HNS enabled), Key Vault (RBAC mode), Data Factory (SystemAssigned identity
present), Databricks workspace. Confirm ADF's managed identity has Storage Blob Data Contributor on
the storage account (the template assigns it). Report a concise summary to the user.

## Phase 3 — Load synthetic data into the lake

The signed-in user needs **data-plane** access to upload (control-plane Owner is not enough):

```bash
SA=<storageAccount from outputs>
SA_ID=$(az storage account show -n "$SA" -g "$RG" --query id -o tsv)
az role assignment create --assignee "$ADMIN_OBJECT_ID" \
  --role "Storage Blob Data Contributor" --scope "$SA_ID"
# RBAC propagation can take 1-5 minutes before the upload below succeeds.

python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m src.generators.generate_all

az storage blob upload-batch --account-name "$SA" --auth-mode login \
  --destination landing --source data/landing --pattern "*.csv" --overwrite
```

## Phase 4 — Run the medallion in Databricks

This step needs a Databricks **personal access token**, which you cannot create yourself.

- **STOP:** Ask the user to create a PAT in the workspace (User Settings -> Developer -> Access
  tokens) and paste it. Then store it in Key Vault and configure the Databricks CLI **in-memory only**:

```bash
KV=<keyVaultName from outputs>
az keyvault secret set --vault-name "$KV" --name databricks-pat --value "<PAT>" >/dev/null

export DATABRICKS_HOST="https://<databricksWorkspaceUrl from outputs>"
export DATABRICKS_TOKEN="<PAT>"     # session env only — never write to a committed file
databricks current-user me          # verify auth (install the databricks CLI if missing)
```

Bring the code into the workspace. Preferred path (after the repo is pushed to GitHub) is a
Databricks Repo so the notebooks find `sql/` at `/Workspace/Repos/...`:

```bash
databricks repos create --url "<your GitHub repo URL>" --provider gitHub \
  --path "/Workspace/Repos/dtbi"
# If the repo is not yet on GitHub, instead: databricks workspace import-dir notebooks <path>
#   and adjust the notebook file-paths accordingly.
```

Run the notebooks in order on a small auto-terminating job cluster (single worker, ~15 min
auto-terminate — do not change these). Run `01_bronze_autoloader` (set its `landing_path` widget to
the ADLS landing container), then `02_silver_transforms`, then `03_gold_marts`, then
`04_unity_catalog_governance`. Use `databricks jobs submit` one-time runs or a small multi-task job;
keep `autotermination_minutes` low. Confirm `dtbi.gold.kpi_overview` and
`dtbi.gold.kpi_predictability_forecast` exist when done.

## Phase 5 — (Optional) Wire ADF orchestration

Only if the user wants scheduled orchestration. The artifacts in `adf/` (linked services, dataset,
pipeline) are easiest to bring in via ADF Studio Git integration; CLI import via `az datafactory`
subcommands also works but is fiddly. The `ls_databricks` linked service reads the PAT from Key Vault
(`databricks-pat`) — confirm a Key Vault linked service named `ls_keyvault` exists/created and that
ADF's identity has `get` on Key Vault secrets. This phase is not required for a working demo; the
Databricks notebooks in Phase 4 already build Gold end to end.

## Phase 6 — Validate and hand off

- Confirm Gold tables/views populated in Unity Catalog (`dtbi.gold.*`).
- The local dashboard reads local Parquet; for a cloud demo, point Power BI / a SQL warehouse at
  `dtbi.gold` per `bi/powerbi/semantic_model.md`. Locally, `make demo` still works independently.
- Summarize for the user: what was created, the resource group, and the estimated idle cost.

## Phase 7 — Teardown (remind the user)

When the demo is finished, stop all billing:

```bash
az group delete --name "${PREFIX}-rg" --yes
```

Then verify the Databricks **managed** resource group (`${PREFIX}-dbw-managed`) is also gone. The
`./scripts/teardown.sh` script does this with a typed confirmation. Always remind the user to run
teardown if they are pausing.

---

## Troubleshooting

- **AuthorizationFailed creating role assignments** during deploy: the signed-in identity needs
  `Owner` or `User Access Administrator` on the subscription (the template creates role assignments).
- **Provider not registered**: complete Phase 0 registration and wait for `Registered`.
- **Storage upload 403 / AuthorizationPermissionMismatch**: the Storage Blob Data Contributor grant
  from Phase 3 hasn't propagated yet, or you used `--auth-mode key` — use `--auth-mode login`.
- **Key Vault name already exists / soft-deleted**: KV has soft-delete; either purge the old vault
  (`az keyvault purge`) or change `resourcePrefix` so the generated name differs.
- **Storage/KV name length or global-uniqueness errors**: change `resourcePrefix` (3-8 lowercase).
- **Databricks workspace URL empty**: the workspace can take a few minutes to finish provisioning;
  re-query the deployment outputs.

## Repo conventions (so your edits stay consistent)

- Transformation logic is SQL-first (`sql/`), Python only for ingestion/generation (`src/`).
- Catalog naming: `dtbi.<layer>.<table>`; KPI views grouped by mission pillar (`kpi_speed_*`,
  `kpi_predictability_*`, `kpi_accessibility_*`).
- Keep the platform aligned to its mission — faster, more predictable, more accessible — when adding
  metrics or marts.
- The local pipeline (`src/pipelines/local_run.py`) must keep working without Azure; run
  `make generate && make run && make test` after changes.
