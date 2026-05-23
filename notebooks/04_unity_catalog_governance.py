# Databricks notebook source
# MAGIC %md
# MAGIC # Unity Catalog — PHI governance (masking, row-level security, RBAC)
# MAGIC Applies least-privilege controls so analysts can build leadership reports without seeing
# MAGIC raw identifiers. See docs/HIPAA_NOTES.md for the policy rationale.

# COMMAND ----------
catalog = "dtbi"
# Column mask: only members of the phi_readers group see raw values; others get a redaction.
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.silver.mask_identifier(val STRING)
RETURN CASE WHEN is_account_group_member('phi_readers') THEN val ELSE '***REDACTED***' END
""")
spark.sql(f"ALTER TABLE {catalog}.silver.dim_patient ALTER COLUMN patient_id SET MASK {catalog}.silver.mask_identifier")

# Row-level security: site staff only see their own site's patients.
spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog}.silver.site_rls(site_id STRING)
RETURN is_account_group_member('all_sites') OR site_id = current_user_site()
""")
spark.sql(f"ALTER TABLE {catalog}.silver.dim_patient SET ROW FILTER {catalog}.silver.site_rls ON (site_id)")

# RBAC: BI team reads Gold only; engineers own Silver/Bronze.
spark.sql(f"GRANT USAGE ON SCHEMA {catalog}.gold TO `bi_team`")
spark.sql(f"GRANT SELECT ON SCHEMA {catalog}.gold TO `bi_team`")
print("Governance applied.")
