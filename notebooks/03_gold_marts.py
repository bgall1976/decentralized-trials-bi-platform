# Databricks notebook source
# MAGIC %md
# MAGIC # Gold — star schema + mission KPI views
# MAGIC Builds dims/facts and the KPI views grouped by mission pillar (Faster / Predictable /
# MAGIC Accessible) from `sql/gold/`, then runs the run-rate enrollment forecast job.

# COMMAND ----------
import os
dbutils.widgets.text("catalog", "dtbi")
catalog = dbutils.widgets.get("catalog")
_ctx_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
REPO_ROOT = "/Workspace" + _ctx_path.rsplit("/notebooks/", 1)[0]
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.gold")
gold_dir = f"{REPO_ROOT}/sql/gold"
for f in sorted(os.listdir(gold_dir)):
    if not f.endswith(".sql"):
        continue
    with open(f"{gold_dir}/{f}") as fh:
        for stmt in [s for s in fh.read().split(";") if s.strip() and not s.strip().startswith("--")]:
            spark.sql(stmt)

# COMMAND ----------
# MORE PREDICTABLE: run-rate enrollment forecast -> dtbi.gold.kpi_predictability_forecast
from pyspark.sql import functions as F, Window
fpe = spark.table(f"{catalog}.gold.fact_patient_enrollment")
study = spark.table(f"{catalog}.gold.dim_study")
today = F.current_date()
recent = (fpe.filter("is_enrolled")
            .filter(F.col("enrolled_date") >= F.date_sub(today, 56))
            .groupBy("study_id").agg((F.count("*") / F.lit(8.0)).alias("weekly_velocity")))
forecast = (study.join(
                fpe.filter("is_enrolled").groupBy("study_id").agg(F.count("*").alias("enrolled_to_date")),
                "study_id", "left")
            .join(recent, "study_id", "left")
            .withColumn("remaining", F.greatest(F.lit(0), F.col("target_enrollment") - F.col("enrolled_to_date")))
            .withColumn("weeks_to_target", F.col("remaining") / F.col("weekly_velocity"))
            .withColumn("projected_completion_date", F.expr("date_add(current_date(), cast(weeks_to_target*7 as int))"))
            .withColumn("on_track", F.col("projected_completion_date") <= F.col("planned_end_date")))
forecast.write.mode("overwrite").saveAsTable(f"{catalog}.gold.kpi_predictability_forecast")
print("Gold + forecast complete.")
