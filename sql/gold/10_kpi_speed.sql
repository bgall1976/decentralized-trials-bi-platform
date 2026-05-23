-- FASTER: velocity and cycle times.
CREATE OR REPLACE VIEW dtbi.gold.kpi_speed_study AS
SELECT s.study_id, s.therapeutic_area, s.phase,
       min(f.enrolled_date) AS first_enrollment_date,
       datediff(min(f.enrolled_date), s.start_date) AS days_to_first_patient,
       count_if(f.is_enrolled) AS enrolled_to_date,
       round(avg(CASE WHEN f.is_enrolled THEN f.days_lead_to_enrolled END), 1) AS avg_days_lead_to_enrolled
FROM dtbi.gold.dim_study s
LEFT JOIN dtbi.gold.fact_patient_enrollment f USING (study_id)
GROUP BY s.study_id, s.therapeutic_area, s.phase, s.start_date;
