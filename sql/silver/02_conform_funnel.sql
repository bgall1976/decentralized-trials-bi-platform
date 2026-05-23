-- Conform funnel events: type-cast, dedup to first occurrence per (patient, stage), incremental.
CREATE TABLE IF NOT EXISTS dtbi.silver.funnel_events (
    patient_id STRING, study_id STRING, site_id STRING, stage STRING, event_date DATE
) USING DELTA;

MERGE INTO dtbi.silver.funnel_events AS tgt
USING (
    SELECT patient_id, study_id, site_id, stage, CAST(event_date AS DATE) AS event_date
    FROM (
        SELECT *, row_number() OVER (PARTITION BY patient_id, stage ORDER BY event_date) AS rn
        FROM dtbi.bronze.funnel_events
        WHERE _ingest_ts > (SELECT COALESCE(max(watermark), TIMESTAMP '1900-01-01')
                            FROM dtbi.silver._load_watermark WHERE table_name = 'funnel_events')
    ) WHERE rn = 1
) AS src
ON tgt.patient_id = src.patient_id AND tgt.stage = src.stage
WHEN NOT MATCHED THEN INSERT *;
