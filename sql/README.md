# SQL (canonical Databricks/Spark SQL)

These are the **production** transformation definitions that run on Databricks against Delta tables
in Unity Catalog. They demonstrate the senior patterns the role asks for: watermark-based
incremental loads, SCD Type 2 dimensions, and idempotent `MERGE` upserts.

The local DuckDB runner (`src/pipelines/local_run.py`) mirrors this logic so the model is runnable
without Azure; minor dialect differences are expected (Spark `MERGE`/Delta vs. DuckDB).

Catalog convention: `dtbi.<layer>.<table>` (e.g. `dtbi.silver.dim_patient`, `dtbi.gold.kpi_overview`).
KPI views are grouped by mission pillar: `kpi_speed_*`, `kpi_predictability_*`, `kpi_accessibility_*`.
