# How I built this, and why

A walkthrough of the design decisions behind this platform, written for anyone reviewing it as a
work sample. The short version: I designed the whole thing backward from one business mission —
**making clinical trials faster, more predictable, and more accessible** — and let that dictate the
data model, not the other way around.

## The framing

A decentralized research organization gets paid for one thing: enrolling the right patients faster
and reaching communities that historically couldn't participate. So the platform's job isn't "move
data" — it's to answer three questions for leadership on demand:

- Are we getting *faster*? (cycle time, velocity)
- Are we *predictable*? (will each study hit target, and when?)
- Are we reaching *more and more representative* patients? (diversity, decentralized reach)

The Gold layer is organized into exactly those three KPI domains (`kpi_speed_*`,
`kpi_predictability_*`, `kpi_accessibility_*`), plus a cross-cutting `kpi_overview`. That mapping is
the spine of the project.

## Architecture in one breath

Four source domains (enrollment/CTMS, clinical, marketing, financial) → ADF watermark-based
incremental ingest → ADLS Gen2 → Databricks medallion (Bronze raw / Silver conformed / Gold marts)
on Delta Lake, governed by Unity Catalog → Power BI semantic model and a dashboard. Full diagram in
the [README](README.md).

## Key decisions and the tradeoffs behind them

**Medallion + Delta Lake.** Bronze is the immutable record of what arrived; Silver is where I
conform and apply business rules; Gold is the consumption contract for BI. This keeps reprocessing
cheap and makes failures debuggable — I can always replay from Bronze.

**SQL-first transformations.** The role is "mostly SQL, some Python," and I think that's correct for
this problem. The modeling logic lives in version-controlled `.sql` files; Python is reserved for
ingestion connectors and synthetic data. SQL is what the next engineer and the BI team can both read.

**SCD Type 2 on `dim_patient`.** In a regulated clinical context, a patient's site or demographic
attributes changing over time is not something you overwrite — you preserve history with effective
dating. That's auditability, and it's the difference between a toy model and one a compliance team
trusts.

**Watermark / CDC incremental loads + idempotent MERGE.** Loads pull only rows newer than the last
successful high-water-mark and upsert with `MERGE`, so a re-run never duplicates data. This is the
pattern that lets a pipeline run on a schedule without a human babysitting it.

**A real run-rate forecast for "predictable."** "Predictable" is easy to gesture at and hard to
ship. I built an actual forecast: recent weekly velocity projects each study's completion date
against its planned end, and flags it on-track or at-risk. That turns a slogan into a number a
program lead can act on.

**DuckDB + Parquet local parity.** Most portfolio repos can't be run by the person reviewing them.
This one runs end to end on a laptop with `make demo` — same medallion logic, same Gold KPIs — while
the production Spark/Delta versions live in the notebooks and `sql/`. I'd rather a reviewer see real
output than read a dead README.

**Subscription-scoped Bicep + managed identities.** One `az deployment sub create` stands up the RG,
ADLS, Key Vault, ADF, and Databricks. ADF authenticates to the lake with a system-assigned managed
identity and pulls its Databricks token from Key Vault — no keys or secrets in source. The
Subscription ID is supplied at deploy time, never committed.

**Unity Catalog for PHI.** Column masking on identifiers, row-level security by site, and RBAC that
gives the BI team `SELECT` on Gold only. Leadership reporting never requires touching raw
identifiers. Rationale is written up in [docs/HIPAA_NOTES.md](docs/HIPAA_NOTES.md).

**Cost discipline.** It's deployable to a personal subscription, so the Databricks cluster is a
single-worker job cluster with low auto-termination, SKUs are minimal, and there's a one-command
teardown. [docs/COST.md](docs/COST.md) explains the levers.

## How each pillar is actually engineered

| Pillar | Engineered as | Lives in |
|---|---|---|
| Faster | days-to-first-patient, lead→enrolled cycle time, weekly site velocity | `kpi_speed_*` |
| More predictable | run-rate forecast vs. plan, on-track/at-risk flag, screen-fail stability | `kpi_predictability_*` |
| More accessible | enrolled-population diversity, % decentralized (community/mobile) reach | `kpi_accessibility_*` |

## The cross-domain proof point

`cost_per_enrolled_usd` deliberately joins three domains — financial (site costs) + marketing (ad
spend) + enrollment (enrolled count). It's there to prove the platform integrates the org's data,
not just one silo, and it happens to be a metric leadership genuinely cares about.

## What I'd harden for production (and would want to discuss)

- Orchestration: move from notebook-chained runs to Databricks Workflows or ADF triggers with
  retries, alerting, and SLA monitoring.
- Data quality: graduate the pytest assertions to Great Expectations / DLT expectations with quarantine.
- Governance: signed BAA, Private Link / VNet-injected Databricks, encryption verification, and
  21 CFR Part 11 audit-trail/e-signature considerations where data drives regulated decisions.
- Forecasting: replace the run-rate projection with a model that accounts for seasonality and site
  ramp curves, with confidence intervals.
- Contracts: schema/data contracts on ingestion so an upstream change fails loudly, not silently.

## Questions this work prepares me to answer

- "Design a pipeline from enrollment + medical sources to BI." → the medallion here, end to end.
- "How do you handle slowly changing attributes / late-arriving data / re-runs?" → SCD2, watermark, MERGE.
- "How do you keep PHI safe while still serving leadership reports?" → Unity Catalog masking/RLS/RBAC + minimum-necessary Gold.
- "How would this scale / what would you change?" → the production-hardening list above.

## Running it

See the [README](README.md): `make demo` for local mode, or the deploy scripts / CI workflow for
Azure. All data is synthetic; there is no real PHI anywhere in this repo.
