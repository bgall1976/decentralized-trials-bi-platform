-- MORE PREDICTABLE: funnel conversion + screen-fail stability. (Run-rate forecast is produced by
-- the forecasting job and written to dtbi.gold.kpi_predictability_forecast.)
CREATE OR REPLACE VIEW dtbi.gold.kpi_predictability_conversion AS
SELECT study_id,
       count(*) AS leads,
       count_if(screened_date IS NOT NULL)   AS screened,
       count_if(randomized_date IS NOT NULL) AS randomized,
       count_if(is_enrolled)                 AS enrolled,
       round(100.0 * (count_if(screened_date IS NOT NULL) - count_if(randomized_date IS NOT NULL))
             / NULLIF(count_if(screened_date IS NOT NULL), 0), 1) AS screen_fail_rate_pct
FROM dtbi.gold.fact_patient_enrollment GROUP BY study_id;
