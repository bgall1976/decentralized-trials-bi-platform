# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — incremental raw ingest with Auto Loader
# MAGIC Lands raw source extracts from ADLS into Delta Bronze tables, append-only, with ingest
# MAGIC metadata. Auto Loader gives us exactly-once, schema-evolving incremental file discovery.

# COMMAND ----------
dbutils.widgets.text("landing_path", "abfss://landing@<storage>.dfs.core.windows.net")
dbutils.widgets.text("catalog", "dtbi")
landing = dbutils.widgets.get("landing_path")
catalog = dbutils.widgets.get("catalog")

SOURCES = ["studies", "sites", "patients", "funnel_events", "visits", "adverse_events",
           "campaigns", "marketing_daily", "study_budgets", "site_costs", "invoices"]

# COMMAND ----------
from pyspark.sql import functions as F

for src in SOURCES:
    (spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", f"{landing}/_schema/{src}")
        .option("header", "true")
        .load(f"{landing}/{src}")
        .withColumn("_ingest_ts", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .writeStream.format("delta")
        .option("checkpointLocation", f"{landing}/_checkpoints/{src}")
        .trigger(availableNow=True)
        .toTable(f"{catalog}.bronze.{src}"))

print("Bronze ingest complete.")
