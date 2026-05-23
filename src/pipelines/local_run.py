"""
Local medallion runner (no Azure required).

Mirrors the cloud Databricks pipeline using DuckDB + Parquet so the full Bronze -> Silver -> Gold
model and the three mission KPI domains are demonstrable on any laptop. The production Spark/Delta
implementations (with SCD Type 2 MERGE and watermark CDC) live in notebooks/ and sql/.

  Bronze : raw landing data + ingest metadata (append-only)
  Silver : cleaned, typed, conformed entities + data-quality-ready
  Gold   : star schema (dims + facts) and KPI views grouped by mission pillar:
             Faster  -> kpi_speed_*     Predictable -> kpi_predictability_*
             Accessible -> kpi_accessibility_*   plus kpi_overview (exec summary)
"""
from __future__ import annotations
import datetime as dt
import duckdb
import pandas as pd

from src.common.config import LANDING, BRONZE, SILVER, GOLD

LANDING_TABLES = [
    "studies", "sites", "patients", "funnel_events", "visits", "adverse_events",
    "campaigns", "marketing_daily", "study_budgets", "site_costs", "invoices",
]


def build_bronze():
    ingest_ts = dt.datetime.now(dt.timezone.utc).isoformat()
    for t in LANDING_TABLES:
        df = pd.read_csv(LANDING / f"{t}.csv")
        df["_ingest_ts"] = ingest_ts
        df["_source_file"] = f"landing/{t}.csv"
        df.to_parquet(BRONZE / f"{t}.parquet", index=False)
    print(f"  Bronze: {len(LANDING_TABLES)} tables -> {BRONZE}")


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in LANDING_TABLES:
        con.execute(f"CREATE VIEW br_{t} AS SELECT * FROM read_parquet('{BRONZE / (t + '.parquet')}')")
    return con


def build_silver(con):
    # Conform + type-cast. Dedup defensively. (Cloud Silver additionally applies SCD2 on dims.)
    con.execute("""
        CREATE TABLE sv_study AS
        SELECT study_id, protocol_number, sponsor, therapeutic_area, phase,
               CAST(target_enrollment AS INTEGER) AS target_enrollment,
               CAST(planned_duration_days AS INTEGER) AS planned_duration_days,
               CAST(start_date AS DATE) AS start_date,
               CAST(start_date AS DATE) + CAST(planned_duration_days AS INTEGER) AS planned_end_date
        FROM br_studies;

        CREATE TABLE sv_site AS
        SELECT site_id, site_name, site_type, region, state,
               CAST(activated_date AS DATE) AS activated_date, pi_name,
               site_type IN ('community','mobile') AS is_decentralized
        FROM br_sites;

        CREATE TABLE sv_patient AS
        SELECT patient_id, study_id, site_id, CAST(age AS INTEGER) AS age, sex, race_ethnicity,
               CAST(is_rural AS BOOLEAN) AS is_rural
        FROM br_patients;

        CREATE TABLE sv_funnel AS
        SELECT patient_id, study_id, site_id, stage, CAST(event_date AS DATE) AS event_date
        FROM (SELECT *, row_number() OVER (PARTITION BY patient_id, stage ORDER BY event_date) rn
              FROM br_funnel_events) WHERE rn = 1;

        CREATE TABLE sv_marketing AS
        SELECT campaign_id, study_id, CAST(activity_date AS DATE) AS activity_date, channel,
               CAST(spend_usd AS DOUBLE) AS spend_usd, CAST(impressions AS BIGINT) AS impressions,
               CAST(clicks AS BIGINT) AS clicks, CAST(leads AS BIGINT) AS leads
        FROM br_marketing_daily;

        CREATE TABLE sv_campaign AS SELECT * FROM br_campaigns;

        CREATE TABLE sv_site_costs AS
        SELECT study_id, site_id, CAST(month AS DATE) AS month,
               CAST(operating_cost_usd AS DOUBLE) AS operating_cost_usd,
               CAST(per_visit_cost_usd AS DOUBLE) AS per_visit_cost_usd
        FROM br_site_costs;

        CREATE TABLE sv_budget AS
        SELECT study_id, currency, CAST(total_budget_usd AS DOUBLE) AS total_budget_usd
        FROM br_study_budgets;
    """)
    for t in ["sv_study", "sv_site", "sv_patient", "sv_funnel", "sv_marketing",
              "sv_campaign", "sv_site_costs", "sv_budget"]:
        con.execute(f"COPY {t} TO '{SILVER / (t[3:] + '.parquet')}' (FORMAT PARQUET)")
    print(f"  Silver: 8 conformed tables -> {SILVER}")


def build_gold(con):
    # ---------- Dimensions ----------
    con.execute("""
        CREATE TABLE dim_study AS SELECT * FROM sv_study;
        CREATE TABLE dim_site  AS SELECT * FROM sv_site;
        CREATE TABLE dim_patient AS SELECT * FROM sv_patient;
        CREATE TABLE dim_campaign AS SELECT * FROM sv_campaign;
        CREATE TABLE dim_date AS
            SELECT d AS date_key, year(d) AS year, month(d) AS month, day(d) AS day,
                   week(d) AS week, dayname(d) AS day_name
            FROM (SELECT unnest(generate_series(DATE '2024-01-01', DATE '2026-12-31',
                  INTERVAL 1 DAY))::DATE AS d);
    """)

    # ---------- fact_patient_enrollment (one row per patient-study) ----------
    con.execute("""
        CREATE TABLE fact_patient_enrollment AS
        WITH ev AS (
            SELECT patient_id, study_id, any_value(site_id) AS site_id,
                   min(CASE WHEN stage='lead'         THEN event_date END) AS lead_date,
                   min(CASE WHEN stage='pre_screened' THEN event_date END) AS pre_screened_date,
                   min(CASE WHEN stage='consented'    THEN event_date END) AS consented_date,
                   min(CASE WHEN stage='screened'     THEN event_date END) AS screened_date,
                   min(CASE WHEN stage='randomized'   THEN event_date END) AS randomized_date,
                   min(CASE WHEN stage='enrolled'     THEN event_date END) AS enrolled_date,
                   min(CASE WHEN stage='completed'    THEN event_date END) AS completed_date
            FROM sv_funnel GROUP BY patient_id, study_id
        )
        SELECT ev.*, p.age, p.sex, p.race_ethnicity, p.is_rural,
               (screened_date IS NOT NULL AND randomized_date IS NULL) AS screen_failed,
               (enrolled_date IS NOT NULL) AS is_enrolled,
               (completed_date IS NOT NULL) AS is_completed,
               date_diff('day', lead_date, enrolled_date)        AS days_lead_to_enrolled,
               date_diff('day', screened_date, randomized_date)  AS days_screened_to_randomized,
               date_diff('day', consented_date, enrolled_date)   AS days_consent_to_enrolled
        FROM ev JOIN sv_patient p USING (patient_id, study_id);
    """)

    # ---------- fact_marketing_daily / fact_site_financials ----------
    con.execute("""
        CREATE TABLE fact_marketing_daily AS SELECT * FROM sv_marketing;
        CREATE TABLE fact_site_financials AS SELECT * FROM sv_site_costs;
    """)

    # ================= MISSION KPI VIEWS =================

    # ----- FASTER -----
    con.execute("""
        CREATE TABLE kpi_speed_study AS
        SELECT s.study_id, s.therapeutic_area, s.phase,
               min(f.enrolled_date) AS first_enrollment_date,
               date_diff('day', s.start_date, min(f.enrolled_date)) AS days_to_first_patient,
               count(*) FILTER (WHERE f.is_enrolled) AS enrolled_to_date,
               round(avg(f.days_lead_to_enrolled) FILTER (WHERE f.is_enrolled), 1) AS avg_days_lead_to_enrolled,
               round(avg(f.days_screened_to_randomized) FILTER (WHERE f.screened_date IS NOT NULL), 1)
                   AS avg_days_screened_to_randomized
        FROM sv_study s LEFT JOIN fact_patient_enrollment f USING (study_id)
        GROUP BY s.study_id, s.therapeutic_area, s.phase, s.start_date;

        CREATE TABLE kpi_speed_site_weekly AS
        SELECT site_id, study_id, date_trunc('week', enrolled_date) AS week_start,
               count(*) AS enrolled_in_week
        FROM fact_patient_enrollment WHERE is_enrolled
        GROUP BY site_id, study_id, date_trunc('week', enrolled_date);
    """)

    # ----- ACCESSIBLE -----
    con.execute("""
        CREATE TABLE kpi_accessibility_diversity AS
        SELECT study_id, race_ethnicity, sex,
               count(*) FILTER (WHERE is_enrolled) AS enrolled,
               round(100.0 * count(*) FILTER (WHERE is_enrolled)
                     / NULLIF(sum(count(*) FILTER (WHERE is_enrolled)) OVER (PARTITION BY study_id), 0), 1)
                   AS pct_of_study_enrolled
        FROM fact_patient_enrollment GROUP BY study_id, race_ethnicity, sex;

        CREATE TABLE kpi_accessibility_reach AS
        SELECT st.site_type, st.region,
               count(*) FILTER (WHERE f.is_enrolled) AS enrolled,
               count(DISTINCT f.site_id) AS sites
        FROM fact_patient_enrollment f JOIN sv_site st USING (site_id)
        GROUP BY st.site_type, st.region;
    """)

    # ----- PREDICTABLE (run-rate forecast computed in pandas below) -----
    con.execute("""
        CREATE TABLE kpi_predictability_conversion AS
        SELECT study_id,
               count(*) AS leads,
               count(*) FILTER (WHERE consented_date  IS NOT NULL) AS consented,
               count(*) FILTER (WHERE screened_date   IS NOT NULL) AS screened,
               count(*) FILTER (WHERE randomized_date IS NOT NULL) AS randomized,
               count(*) FILTER (WHERE is_enrolled) AS enrolled,
               round(100.0 * count(*) FILTER (WHERE randomized_date IS NOT NULL)
                     / NULLIF(count(*) FILTER (WHERE screened_date IS NOT NULL),0), 1) AS pass_rate_pct,
               round(100.0 * (count(*) FILTER (WHERE screened_date IS NOT NULL)
                     - count(*) FILTER (WHERE randomized_date IS NOT NULL))
                     / NULLIF(count(*) FILTER (WHERE screened_date IS NOT NULL),0), 1) AS screen_fail_rate_pct
        FROM fact_patient_enrollment GROUP BY study_id;
    """)

    forecast = build_forecast(con)
    con.register("forecast_df", forecast)
    con.execute("CREATE TABLE kpi_predictability_forecast AS SELECT * FROM forecast_df")

    # ----- EXEC OVERVIEW: one row per study across all three pillars + cost -----
    con.execute("""
        CREATE TABLE kpi_overview AS
        SELECT s.study_id, s.therapeutic_area, s.phase, s.target_enrollment,
               sp.enrolled_to_date,
               sp.days_to_first_patient,                                   -- Faster
               fc.projected_completion_date, fc.on_track,                  -- Predictable
               acc.pct_decentralized_enrolled,                             -- Accessible
               cost.cost_per_enrolled_usd                                  -- Efficiency
        FROM sv_study s
        LEFT JOIN kpi_speed_study sp USING (study_id)
        LEFT JOIN kpi_predictability_forecast fc USING (study_id)
        LEFT JOIN (
            SELECT f.study_id,
                   round(100.0 * count(*) FILTER (WHERE f.is_enrolled AND st.is_decentralized)
                         / NULLIF(count(*) FILTER (WHERE f.is_enrolled),0),1) AS pct_decentralized_enrolled
            FROM fact_patient_enrollment f JOIN sv_site st USING (site_id) GROUP BY f.study_id
        ) acc USING (study_id)
        LEFT JOIN (
            SELECT e.study_id,
                   round((COALESCE(sc.total_op_cost,0)+COALESCE(mk.total_spend,0))
                         / NULLIF(count(*) FILTER (WHERE e.is_enrolled),0),0) AS cost_per_enrolled_usd
            FROM fact_patient_enrollment e
            LEFT JOIN (SELECT study_id, sum(operating_cost_usd) AS total_op_cost FROM sv_site_costs GROUP BY study_id) sc
                   ON sc.study_id = e.study_id
            LEFT JOIN (SELECT study_id, sum(spend_usd) AS total_spend FROM sv_marketing GROUP BY study_id) mk
                   ON mk.study_id = e.study_id
            GROUP BY e.study_id, sc.total_op_cost, mk.total_spend
        ) cost USING (study_id);
    """)

    gold_tables = [
        "dim_study", "dim_site", "dim_patient", "dim_campaign", "dim_date",
        "fact_patient_enrollment", "fact_marketing_daily", "fact_site_financials",
        "kpi_speed_study", "kpi_speed_site_weekly",
        "kpi_accessibility_diversity", "kpi_accessibility_reach",
        "kpi_predictability_conversion", "kpi_predictability_forecast",
        "kpi_overview",
    ]
    for t in gold_tables:
        con.execute(f"COPY {t} TO '{GOLD / (t + '.parquet')}' (FORMAT PARQUET)")
    print(f"  Gold: {len(gold_tables)} tables (dims, facts, mission KPI views) -> {GOLD}")


def build_forecast(con) -> pd.DataFrame:
    """Run-rate enrollment forecast -> the heart of 'More Predictable'.

    Uses recent weekly enrollment velocity to project total enrolled at the planned end date and
    the date the study is on pace to hit its target, then flags at-risk studies.
    """
    enr = con.execute("""
        SELECT study_id, enrolled_date FROM fact_patient_enrollment WHERE is_enrolled
    """).df()
    studies = con.execute("""
        SELECT study_id, target_enrollment, start_date, planned_end_date FROM sv_study
    """).df()
    today = pd.Timestamp("2026-05-01")
    rows = []
    for _, s in studies.iterrows():
        e = enr[enr.study_id == s.study_id].copy()
        enrolled_to_date = len(e)
        # velocity over the most recent 8 weeks
        recent = e[pd.to_datetime(e.enrolled_date) >= (today - pd.Timedelta(weeks=8))]
        weekly_velocity = round(len(recent) / 8.0, 2)
        planned_end = pd.Timestamp(s.planned_end_date)
        weeks_remaining = max(0, (planned_end - today).days / 7.0)
        projected_at_plan_end = int(enrolled_to_date + weekly_velocity * weeks_remaining)
        remaining = max(0, s.target_enrollment - enrolled_to_date)
        if weekly_velocity > 0:
            weeks_to_target = remaining / weekly_velocity
            projected_completion = (today + pd.Timedelta(weeks=weeks_to_target)).date()
        else:
            projected_completion = None
        pct_to_target = round(100.0 * enrolled_to_date / s.target_enrollment, 1)
        on_track = bool(projected_completion is not None and pd.Timestamp(projected_completion) <= planned_end)
        rows.append({
            "study_id": s.study_id, "target_enrollment": int(s.target_enrollment),
            "enrolled_to_date": enrolled_to_date, "pct_to_target": pct_to_target,
            "weekly_velocity": weekly_velocity, "projected_at_plan_end": projected_at_plan_end,
            "planned_end_date": planned_end.date(),
            "projected_completion_date": projected_completion, "on_track": on_track,
            "status": "On track" if on_track else "At risk",
        })
    return pd.DataFrame(rows)


def main():
    print("Running local medallion pipeline (DuckDB + Parquet)...")
    build_bronze()
    con = _con()
    build_silver(con)
    build_gold(con)
    con.close()
    print("Done. Gold layer is ready for the dashboard (bi/dashboard/app.py).")


if __name__ == "__main__":
    main()
