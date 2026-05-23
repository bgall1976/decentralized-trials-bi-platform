-- Gold dimensions (conformed). dim_patient is the SCD2 current-version projection for marts.
-- Columns are listed explicitly (instead of `SELECT * EXCEPT (...)`) to avoid a Databricks Runtime
-- 16.x analyzer issue where RowColumnControlsAllowlistRule triggers on an unresolved Star.
CREATE OR REPLACE VIEW dtbi.gold.dim_patient AS
    SELECT patient_sk, patient_id, study_id, site_id, age, sex, race_ethnicity, is_rural
    FROM dtbi.silver.dim_patient WHERE is_current = true;

CREATE OR REPLACE TABLE dtbi.gold.dim_study  USING DELTA AS
    SELECT CAST(study_id AS STRING) AS study_id,
           CAST(protocol_number AS STRING) AS protocol_number,
           CAST(sponsor AS STRING) AS sponsor,
           CAST(therapeutic_area AS STRING) AS therapeutic_area,
           CAST(phase AS STRING) AS phase,
           CAST(target_enrollment AS INT) AS target_enrollment,
           CAST(planned_duration_days AS INT) AS planned_duration_days,
           CAST(start_date AS DATE) AS start_date,
           date_add(CAST(start_date AS DATE), CAST(planned_duration_days AS INT)) AS planned_end_date
    FROM dtbi.bronze.studies;
CREATE OR REPLACE TABLE dtbi.gold.dim_site   USING DELTA AS
    SELECT CAST(site_id AS STRING) AS site_id,
           CAST(site_name AS STRING) AS site_name,
           CAST(site_type AS STRING) AS site_type,
           CAST(region AS STRING) AS region,
           CAST(state AS STRING) AS state,
           CAST(activated_date AS DATE) AS activated_date,
           CAST(pi_name AS STRING) AS pi_name
    FROM dtbi.bronze.sites;
CREATE OR REPLACE TABLE dtbi.gold.dim_date   USING DELTA AS
    SELECT explode(sequence(DATE'2024-01-01', DATE'2026-12-31', INTERVAL 1 DAY)) AS date_key;
