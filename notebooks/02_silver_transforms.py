# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — conform, cleanse, SCD Type 2
# MAGIC Runs the canonical SQL in `sql/silver/`. Demonstrates watermark-based incremental loads and
# MAGIC SCD2 history on dim_patient. PHI columns are governed by Unity Catalog (see masking notebook).

# COMMAND ----------
dbutils.widgets.text("catalog", "dtbi")
catalog = dbutils.widgets.get("catalog")
# Locate the repo root relative to this notebook so the SQL files are found no matter where the
# Git folder lives in the workspace (legacy /Workspace/Repos/dtbi/... was hardcoded previously).
_ctx_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
REPO_ROOT = "/Workspace" + _ctx_path.rsplit("/notebooks/", 1)[0]
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.silver")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {catalog}.silver._load_watermark
              (table_name STRING, watermark TIMESTAMP) USING DELTA""")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {catalog}.silver.dim_patient
              (patient_sk STRING, patient_id STRING, study_id STRING, site_id STRING, age INT,
               sex STRING, race_ethnicity STRING, is_rural BOOLEAN,
               effective_from TIMESTAMP, effective_to TIMESTAMP, is_current BOOLEAN) USING DELTA""")

# COMMAND ----------
# Execute each statement in the versioned SQL files (kept in the repo as the source of truth).
import os
silver_dir = f"{REPO_ROOT}/sql/silver"
for f in sorted(os.listdir(silver_dir)):
    with open(f"{silver_dir}/{f}") as fh:
        for stmt in [s for s in fh.read().split(";") if s.strip() and not s.strip().startswith("--")]:
            spark.sql(stmt)
print("Silver build complete.")
