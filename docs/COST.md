# Cost notes (personal subscription)

This is built to be cheap to stand up and easy to tear down. **Run `./scripts/teardown.sh` when done.**

## What drives cost
- **Databricks** is the main lever — you pay for cluster *uptime* (DBUs + the underlying VMs). The
  linked service and notebooks use a **single-worker `Standard_DS3_v2`** job cluster; configure
  **auto-termination (~15 min)** so idle clusters don't bill. Job clusters (created per run) are
  cheaper than an always-on interactive cluster.
- **ADLS Gen2** — Standard LRS, a few MB of synthetic CSV/Delta. Effectively pennies.
- **Azure Data Factory** — consumption-based; trivial at this volume (per-activity + per-pipeline-run).
- **Key Vault** — standard tier; per-operation, negligible.

## Guardrails in this repo
- Smallest reasonable SKUs in `infra/modules/*` (Standard_LRS, standard Key Vault, standard Databricks).
- Single-worker, version-pinned, fixed job cluster in `adf/linkedservices/ls_databricks.json`.
- `scripts/teardown.sh` deletes the whole resource group; remember Databricks also creates a
  **managed resource group** (`<prefix>-dbw-managed`) — verify it's removed after teardown.

## Rough expectation
Idle (everything deployed, nothing running): roughly storage + Key Vault only — cents/day. Cost
appears mainly while a Databricks cluster is actively running a pipeline. Tear down between demos.
