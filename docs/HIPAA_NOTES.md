# HIPAA / PHI governance notes

All data in this repo is **synthetic** — there is no real PHI. The controls below document how the
platform would handle real PHI in production, which is the relevant signal for a clinical-data role.

## Principles
- **Minimum necessary.** The BI team and leadership consume **Gold**, which carries aggregates and
  de-identified attributes — not raw identifiers. Engineers work in Silver/Bronze under tighter RBAC.
- **Least privilege via Unity Catalog.** See `notebooks/04_unity_catalog_governance.py`:
  - *Column masking* on direct identifiers (e.g. `patient_id`) — non-`phi_readers` see a redaction.
  - *Row-level security* so site staff see only their own site's records.
  - *RBAC* — `bi_team` gets `SELECT` on Gold only; Bronze/Silver restricted to engineering.
- **Auditability.** SCD Type 2 on `dim_patient` preserves attribute history with effective dating.
  Delta time travel + Unity Catalog audit logs cover who-read-what.
- **Secrets.** No credentials in git. ADF uses a managed identity; the Databricks PAT lives in
  Key Vault. `.bicepparam`, `.env`, and tokens are gitignored.

## Out of scope for a demo (note in interview)
A production deployment would also need a signed BAA with Microsoft, encryption-at-rest/in-transit
verification (default on for ADLS/Delta), de-identification review against HIPAA Safe Harbor /
Expert Determination, network isolation (Private Link / VNet-injected Databricks), and 21 CFR Part 11
considerations (audit trails, e-signatures) where the data supports regulated decisions.
