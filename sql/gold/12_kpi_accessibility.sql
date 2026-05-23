-- MORE ACCESSIBLE: diversity of enrolled population + decentralized (community/mobile) reach.
CREATE OR REPLACE VIEW dtbi.gold.kpi_accessibility_diversity AS
SELECT study_id, race_ethnicity, sex, count_if(is_enrolled) AS enrolled,
       round(100.0 * count_if(is_enrolled)
             / NULLIF(sum(count_if(is_enrolled)) OVER (PARTITION BY study_id), 0), 1) AS pct_of_study_enrolled
FROM dtbi.gold.fact_patient_enrollment GROUP BY study_id, race_ethnicity, sex;

CREATE OR REPLACE VIEW dtbi.gold.kpi_accessibility_reach AS
SELECT st.site_type, st.region, count_if(f.is_enrolled) AS enrolled,
       count(DISTINCT f.site_id) AS sites
FROM dtbi.gold.fact_patient_enrollment f JOIN dtbi.gold.dim_site st USING (site_id)
GROUP BY st.site_type, st.region;
