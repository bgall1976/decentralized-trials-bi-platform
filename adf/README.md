# Azure Data Factory artifacts

ADF orchestrates ingestion and the medallion build. The pipeline `pl_ingest_and_transform`:

1. Looks up the per-source high-water-marks.
2. Incrementally copies only new source data into Bronze (adds an `_ingest_ts` column).
3. Runs the Silver and Gold Databricks notebooks (which include the SCD2 MERGE and the forecast).

Auth is via ADF's **system-assigned managed identity** (Storage Blob Data Contributor on the lake);
the Databricks PAT is read from **Key Vault** at runtime. No credentials are stored in these JSON
files. Import them via ADF Studio git integration or `az datafactory` after `make deploy`.
