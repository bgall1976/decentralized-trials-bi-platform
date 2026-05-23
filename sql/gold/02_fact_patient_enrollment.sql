-- One row per patient-study with milestone dates + derived cycle times (powers Faster + Predictable).
CREATE OR REPLACE TABLE dtbi.gold.fact_patient_enrollment USING DELTA AS
WITH ev AS (
    SELECT patient_id, study_id, any_value(site_id) AS site_id,
           min(CASE WHEN stage='lead'       THEN event_date END) AS lead_date,
           min(CASE WHEN stage='consented'  THEN event_date END) AS consented_date,
           min(CASE WHEN stage='screened'   THEN event_date END) AS screened_date,
           min(CASE WHEN stage='randomized' THEN event_date END) AS randomized_date,
           min(CASE WHEN stage='enrolled'   THEN event_date END) AS enrolled_date,
           min(CASE WHEN stage='completed'  THEN event_date END) AS completed_date
    FROM dtbi.silver.funnel_events GROUP BY patient_id, study_id
)
SELECT ev.patient_id, ev.study_id, ev.site_id,
       ev.lead_date, ev.consented_date, ev.screened_date,
       ev.randomized_date, ev.enrolled_date, ev.completed_date,
       p.age, p.sex, p.race_ethnicity, p.is_rural,
       (ev.screened_date IS NOT NULL AND ev.randomized_date IS NULL) AS screen_failed,
       (ev.enrolled_date IS NOT NULL) AS is_enrolled,
       datediff(ev.enrolled_date, ev.lead_date)       AS days_lead_to_enrolled,
       datediff(ev.randomized_date, ev.screened_date) AS days_screened_to_randomized
FROM ev JOIN dtbi.gold.dim_patient p USING (patient_id, study_id);
