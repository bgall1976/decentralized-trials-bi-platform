-- Gold dimensions (conformed). dim_patient is the SCD2 current-version projection for marts.
-- Columns are listed explicitly (instead of `SELECT * EXCEPT (...)`) to avoid a Databricks Runtime
-- 16.x analyzer issue where RowColumnControlsAllowlistRule triggers on an unresolved Star.
CREATE OR REPLACE VIEW dtbi.gold.dim_patient AS
    SELECT patient_sk, patient_id, study_id, site_id, age, sex, race_ethnicity, is_rural
    FROM dtbi.silver.dim_patient WHERE is_current = true;

CREATE OR REPLACE TABLE dtbi.gold.dim_study  USING DELTA AS
    SELECT study_id, protocol_number, sponsor, therapeutic_area, phase,
           target_enrollment, planned_duration_days, start_date,
           date_add(start_date, planned_duration_days) AS planned_end_date
    FROM dtbi.bronze.studies;
CREATE OR REPLACE TABLE dtbi.gold.dim_site   USING DELTA AS
    SELECT site_id, site_name, site_type, region, state, activated_date, pi_name
    FROM dtbi.bronze.sites;
CREATE OR REPLACE TABLE dtbi.gold.dim_date   USING DELTA AS
    SELECT explode(sequence(DATE'2024-01-01', DATE'2026-12-31', INTERVAL 1 DAY)) AS date_key;
