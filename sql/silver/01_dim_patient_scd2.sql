-- Silver dim_patient with SCD Type 2 history.
-- Tracks changes to a patient's site/demographic attributes over time (effective dating).
-- Idempotent: re-running only closes/opens rows when an attribute actually changed.

MERGE INTO dtbi.silver.dim_patient AS tgt
USING (
    SELECT patient_id, study_id, site_id, age, sex, race_ethnicity, is_rural,
           current_timestamp() AS effective_from
    FROM dtbi.bronze.patients
    -- watermark: only rows ingested since the last successful load
    WHERE _ingest_ts > (SELECT COALESCE(max(watermark), TIMESTAMP '1900-01-01')
                        FROM dtbi.silver._load_watermark WHERE table_name = 'dim_patient')
) AS src
ON tgt.patient_id = src.patient_id AND tgt.is_current = true
WHEN MATCHED AND (
        tgt.site_id        <> src.site_id
     OR tgt.race_ethnicity <> src.race_ethnicity
     OR tgt.is_rural       <> src.is_rural
) THEN UPDATE SET tgt.is_current = false, tgt.effective_to = src.effective_from
WHEN NOT MATCHED THEN INSERT
    (patient_sk, patient_id, study_id, site_id, age, sex, race_ethnicity, is_rural,
     effective_from, effective_to, is_current)
    VALUES (uuid(), src.patient_id, src.study_id, src.site_id, src.age, src.sex,
            src.race_ethnicity, src.is_rural, src.effective_from, NULL, true);

-- Insert the new current versions for the rows we just closed (Type 2 second step).
INSERT INTO dtbi.silver.dim_patient
SELECT uuid(), s.patient_id, s.study_id, s.site_id, s.age, s.sex, s.race_ethnicity, s.is_rural,
       current_timestamp(), NULL, true
FROM dtbi.bronze.patients s
JOIN dtbi.silver.dim_patient t
  ON t.patient_id = s.patient_id AND t.is_current = false AND t.effective_to = current_timestamp()
WHERE NOT EXISTS (SELECT 1 FROM dtbi.silver.dim_patient c
                  WHERE c.patient_id = s.patient_id AND c.is_current = true);

-- advance the watermark
MERGE INTO dtbi.silver._load_watermark w
USING (SELECT 'dim_patient' AS table_name, max(_ingest_ts) AS watermark FROM dtbi.bronze.patients) u
ON w.table_name = u.table_name
WHEN MATCHED THEN UPDATE SET w.watermark = u.watermark
WHEN NOT MATCHED THEN INSERT (table_name, watermark) VALUES (u.table_name, u.watermark);
