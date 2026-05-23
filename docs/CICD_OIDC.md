# CI/CD: deploy to Azure with GitHub OIDC (no stored secrets)

This repo deploys to Azure using **OpenID Connect federated credentials**, so GitHub Actions
authenticates to Azure with a short-lived token instead of a stored client secret. The only repo
"secrets" are non-sensitive identifiers (GUIDs). The deploy and teardown workflows are **manual
(`workflow_dispatch`) only** to protect a personal subscription from accidental spend.

## One-time setup

Run these locally with the Azure CLI (logged in to the target subscription). Replace
`<OWNER>/<REPO>` with your GitHub repo.

```bash
SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# 1. Create an Entra app + service principal for GitHub
APP_ID=$(az ad app create --display-name "dtbi-github-oidc" --query appId -o tsv)
az ad sp create --id "$APP_ID"
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# 2. Federated credentials: allow this repo's deploy workflows to request a token.
#    One for the 'azure' environment, one for the main branch.
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "gh-env-azure",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:environment:azure",
  "audiences": ["api://AzureADTokenExchange"]
}'
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "gh-branch-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<OWNER>/<REPO>:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# 3. RBAC. The template creates role assignments (Key Vault + Storage), which requires the
#    deployer to manage access. On a personal subscription, Owner is simplest:
az role assignment create --assignee "$APP_ID" --role "Owner" --scope "/subscriptions/$SUB_ID"
#    (Tighter alternative: "Contributor" + "User Access Administrator".)

echo "AZURE_CLIENT_ID            = $APP_ID"
echo "AZURE_TENANT_ID            = $TENANT_ID"
echo "AZURE_SUBSCRIPTION_ID      = $SUB_ID"
echo "AZURE_DEPLOYER_OBJECT_ID   = $SP_OBJECT_ID"
```

## Add the four repo secrets

GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | the app's `appId` |
| `AZURE_TENANT_ID` | your tenant id |
| `AZURE_SUBSCRIPTION_ID` | target subscription id |
| `AZURE_DEPLOYER_OBJECT_ID` | the service principal's object id (granted Key Vault access by the template) |

These are identifiers, not passwords — there is no client secret to leak.

## Optional approval gate

Settings → Environments → **azure** → add yourself as a **required reviewer**. Both the deploy and
teardown workflows target this environment, so each run pauses for your approval before touching Azure.

## Run it

- **Deploy:** Actions tab → "Deploy to Azure (OIDC)" → Run workflow (pick region/prefix). Then run
  `./scripts/post_deploy.sh` locally to load synthetic data and store the Databricks PAT in Key Vault.
- **Teardown:** Actions tab → "Teardown Azure (OIDC)" → type `<prefix>-rg` to confirm.
