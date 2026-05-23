# Architecture

The platform is a medallion (Bronze → Silver → Gold) lakehouse on Azure Databricks, fed by Azure
Data Factory and served to Power BI. It is designed backward from the mission — **faster, more
predictable, more accessible** — so the Gold layer's job is to answer those three questions for
leadership.

## Layers

**Bronze (raw).** ADF lands source extracts into ADLS Gen2; Databricks Auto Loader ingests them
incrementally into Delta tables, append-only, stamped with `_ingest_ts` and `_source_file`. No
business logic — Bronze is the immutable record of what arrived.

**Silver (conformed).** Type-cast, deduplicated, conformed entities. `dim_patient` is maintained as
**SCD Type 2** (effective dating + current flag) so demographic/site changes are auditable — which
matters in a regulated clinical context. Loads are **watermark-based incremental** (only rows newer
than the last successful load). PHI columns are governed here by Unity Catalog (masking + RLS).

**Gold (marts).** A star schema (`fact_patient_enrollment`, `fact_marketing_daily`,
`fact_site_financials` + conformed dims) plus KPI views grouped by mission pillar:

| Pillar | Views | Key measures |
|---|---|---|
| Faster | `kpi_speed_study`, `kpi_speed_site_weekly` | days-to-first-patient, lead→enrolled cycle time, weekly velocity |
| More predictable | `kpi_predictability_conversion`, `kpi_predictability_forecast` | run-rate forecast, projected completion vs. plan, screen-fail rate, on-track flag |
| More accessible | `kpi_accessibility_diversity`, `kpi_accessibility_reach` | enrolled-population diversity, decentralized (community/mobile) share, geographic reach |
| (cross-cutting) | `kpi_overview` | one row per study spanning all three pillars + cost/enrolled |

## The four data domains and why each matters to the mission

- **Enrollment / CTMS** — the funnel itself; the raw material for speed and predictability.
- **Clinical / medical** — visits and adverse events; PHI-sensitive, governed tightly.
- **Marketing** — lead-gen spend; ties recruitment investment to enrolled patients (CAC, accessibility reach).
- **Financial** — budgets, site costs, invoices; powers cost-per-enrolled and study economics.

## Cross-domain proof point

`cost_per_enrolled_usd` in `kpi_overview` joins **financial** (site costs) + **marketing** (spend) +
**enrollment** (enrolled count) — demonstrating the platform integrates all domains, not just one.

## Local vs. cloud parity

`src/pipelines/local_run.py` reproduces this model with DuckDB + Parquet so it runs with no Azure.
The production Spark/Delta versions live in `notebooks/` and `sql/`. Logic is equivalent; only the
engine and a few dialect details differ.
