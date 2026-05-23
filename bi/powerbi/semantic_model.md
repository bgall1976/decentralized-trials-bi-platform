# Power BI semantic model

The BI team builds leadership reports on top of the Gold layer (DirectQuery to the Databricks SQL
warehouse, or Import). This is the model spec the dashboard mirrors. `.pbix` is binary so it isn't
committed; this spec + `measures.dax` is the reproducible source of truth.

## Tables (from `dtbi.gold`)
- `fact_patient_enrollment` (fact) — grain: patient × study
- `fact_marketing_daily` (fact) — grain: campaign × day
- `fact_site_financials` (fact) — grain: site × study × month
- `dim_study`, `dim_site`, `dim_patient`, `dim_campaign`, `dim_date` (dimensions)

## Relationships (single-direction, one-to-many from dim → fact)
- `dim_study[study_id]` → `fact_patient_enrollment[study_id]`, `fact_marketing_daily[study_id]`, `fact_site_financials[study_id]`
- `dim_site[site_id]`   → `fact_patient_enrollment[site_id]`, `fact_site_financials[site_id]`
- `dim_campaign[campaign_id]` → `fact_marketing_daily[campaign_id]`
- `dim_date[date_key]`  → `fact_patient_enrollment[enrolled_date]` (active), other date roles via USERELATIONSHIP

## Report pages (mirror the mission)
1. **Executive overview** — cards from `kpi_overview`, study scorecard.
2. **Faster** — days-to-first-patient, cycle-time bars, weekly velocity line.
3. **More predictable** — forecast vs. target, on-track/at-risk, screen-fail trend.
4. **More accessible** — diversity breakdown, decentralized-reach map by region/site type.

See `measures.dax` for the measures behind each page.
