# Data dictionary (Gold)

## fact_patient_enrollment — grain: one row per patient per study
| column | type | notes |
|---|---|---|
| patient_id, study_id | string | composite key |
| site_id | string | FK → dim_site |
| lead_date … completed_date | date | first timestamp the patient reached each funnel stage |
| screen_failed | bool | screened but not randomized |
| is_enrolled, is_completed | bool | milestone flags |
| days_lead_to_enrolled | int | Faster: total cycle time |
| days_screened_to_randomized | int | Faster: eligibility decision time |
| age, sex, race_ethnicity, is_rural | — | Accessible: demographics for diversity |

## kpi_predictability_forecast — grain: one row per study
| column | notes |
|---|---|
| enrolled_to_date, target_enrollment, pct_to_target | progress |
| weekly_velocity | enrolled/week over the last 8 weeks |
| projected_completion_date | date the study is on pace to hit target |
| planned_end_date, on_track, status | At risk if projected completion > planned end |

## kpi_accessibility_diversity — grain: study × race_ethnicity × sex
`enrolled`, `pct_of_study_enrolled` (sums to ~100% per study).

## kpi_overview — grain: one row per study
Headline metrics across all three pillars + `cost_per_enrolled_usd` (financial + marketing ÷ enrolled).

Dimensions: `dim_study`, `dim_site` (incl. `site_type`, `is_decentralized`), `dim_patient`
(SCD2 current view), `dim_campaign`, `dim_date`.
