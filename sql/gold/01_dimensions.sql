-- Gold dimensions (conformed). dim_patient_current is the SCD2 current-version view for marts.
CREATE OR REPLACE VIEW dtbi.gold.dim_patient AS
    SELECT * EXCEPT (effective_from, effective_to, is_current)
    FROM dtbi.silver.dim_patient WHERE is_current = true;

CREATE OR REPLACE TABLE dtbi.gold.dim_study  USING DELTA AS SELECT * FROM dtbi.silver.study;
CREATE OR REPLACE TABLE dtbi.gold.dim_site   USING DELTA AS SELECT * FROM dtbi.silver.site;
CREATE OR REPLACE TABLE dtbi.gold.dim_date   USING DELTA AS
    SELECT explode(sequence(DATE'2024-01-01', DATE'2026-12-31', INTERVAL 1 DAY)) AS date_key;
