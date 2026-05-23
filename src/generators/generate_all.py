"""
Synthetic source-data generator for the decentralized-trials BI platform.

Produces realistic (but entirely fake) extracts for the four domains a decentralized research
org runs on. Deterministic given SEED so runs are reproducible.

Mission alignment baked into the data shape:
  * Faster        -> realistic stage timestamps so cycle times / velocity are measurable
  * Predictable   -> a per-study enrollment ramp so a forecast vs. target is meaningful
  * Accessible    -> community/mobile site types + demographic mix so reach & diversity are real
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import date, timedelta
from faker import Faker

from src.common.config import LANDING, SEED, FUNNEL_STAGES

fake = Faker()
Faker.seed(SEED)
rng = np.random.default_rng(SEED)

TODAY = date(2026, 5, 1)
THERAPEUTIC_AREAS = ["Neurology", "Oncology", "Cardiology", "Immunology", "Psychiatry", "Metabolic"]
PHASES = ["Phase I", "Phase II", "Phase III"]
SITE_TYPES = ["community", "mobile", "fixed"]          # decentralized footprint -> accessibility
REGIONS = ["Northeast", "Southeast", "Midwest", "West", "Southwest"]
RACE_ETHNICITY = ["White", "Black or African American", "Hispanic or Latino",
                  "Asian", "American Indian or Alaska Native", "Other / Multiple"]
SEXES = ["Female", "Male"]


def _daterange(start: date, end: date) -> int:
    return (end - start).days


def gen_studies(n: int = 6) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        start = TODAY - timedelta(days=int(rng.integers(120, 540)))
        rows.append({
            "study_id": f"STU-{i:03d}",
            "protocol_number": f"{rng.choice(THERAPEUTIC_AREAS)[:3].upper()}-{rng.integers(1000,9999)}",
            "sponsor": fake.company(),
            "therapeutic_area": rng.choice(THERAPEUTIC_AREAS),
            "phase": rng.choice(PHASES),
            "target_enrollment": int(rng.integers(150, 600)),
            "planned_duration_days": int(rng.integers(240, 540)),
            "start_date": start.isoformat(),
        })
    return pd.DataFrame(rows)


def gen_sites(n: int = 40) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        activated = TODAY - timedelta(days=int(rng.integers(60, 600)))
        rows.append({
            "site_id": f"SITE-{i:03d}",
            "site_name": f"{fake.city()} Research {rng.choice(['Center','Clinic','Partners'])}",
            "site_type": rng.choice(SITE_TYPES, p=[0.45, 0.25, 0.30]),
            "region": rng.choice(REGIONS),
            "state": fake.state_abbr(),
            "activated_date": activated.isoformat(),
            "pi_name": f"Dr. {fake.last_name()}",
        })
    return pd.DataFrame(rows)


def gen_patients_and_funnel(studies: pd.DataFrame, sites: pd.DataFrame):
    """Generate patients and their funnel event log with realistic per-stage attrition + timing."""
    patients, events, visits, aes = [], [], [], []
    pid = 0
    # stage-to-stage conversion probabilities (the 'screened -> randomized' step is the screen pass)
    conv = {
        "lead": 0.62,          # lead -> pre_screened
        "pre_screened": 0.55,  # -> consented
        "consented": 0.80,     # -> screened
        "screened": 0.68,      # -> randomized  (1 - screen-fail rate ~32%)
        "randomized": 0.97,    # -> enrolled
        "enrolled": 0.85,      # -> completed
    }
    site_ids = sites["site_id"].tolist()
    for _, st in studies.iterrows():
        study_start = date.fromisoformat(st["start_date"])
        # number of leads scaled to target so enrollment lands near (but not exactly) target
        n_leads = int(st["target_enrollment"] / (np.prod(list(conv.values())[:5])) * rng.uniform(0.9, 1.25))
        for _ in range(n_leads):
            pid += 1
            patient_id = f"PT-{pid:06d}"
            site_id = rng.choice(site_ids)
            age = int(np.clip(rng.normal(54, 16), 18, 89))
            race = rng.choice(RACE_ETHNICITY, p=[0.40, 0.18, 0.20, 0.10, 0.04, 0.08])
            sex = rng.choice(SEXES)
            patients.append({
                "patient_id": patient_id, "study_id": st["study_id"], "site_id": site_id,
                "age": age, "sex": sex, "race_ethnicity": race,
                "is_rural": bool(rng.random() < 0.22),
            })
            # walk the funnel
            t = study_start + timedelta(days=int(rng.integers(0, max(1, st["planned_duration_days"] - 30))))
            reached = "lead"
            events.append({"patient_id": patient_id, "study_id": st["study_id"], "site_id": site_id,
                           "stage": "lead", "event_date": t.isoformat()})
            for stage in FUNNEL_STAGES[:-1]:
                if stage not in conv:
                    break
                if rng.random() <= conv[stage]:
                    gap = int(np.clip(rng.exponential(9), 1, 90))   # realistic waiting time -> Faster
                    t = t + timedelta(days=gap)
                    if t > TODAY:
                        break
                    nxt = FUNNEL_STAGES[FUNNEL_STAGES.index(stage) + 1]
                    events.append({"patient_id": patient_id, "study_id": st["study_id"],
                                   "site_id": site_id, "stage": nxt, "event_date": t.isoformat()})
                    reached = nxt
                else:
                    break
            # clinical records for enrolled patients
            if reached in ("enrolled", "completed"):
                n_visits = int(rng.integers(2, 9))
                for v in range(1, n_visits + 1):
                    vdate = t + timedelta(days=v * int(rng.integers(14, 35)))
                    if vdate > TODAY:
                        break
                    visits.append({"visit_id": f"V-{pid:06d}-{v:02d}", "patient_id": patient_id,
                                   "study_id": st["study_id"], "visit_number": v,
                                   "visit_date": vdate.isoformat(),
                                   "status": rng.choice(["completed", "missed"], p=[0.92, 0.08])})
                if rng.random() < 0.25:
                    aes.append({"ae_id": f"AE-{pid:06d}", "patient_id": patient_id,
                                "study_id": st["study_id"],
                                "severity": rng.choice(["mild", "moderate", "severe"], p=[0.6, 0.32, 0.08]),
                                "serious_flag": bool(rng.random() < 0.12),
                                "onset_date": (t + timedelta(days=int(rng.integers(5, 120)))).isoformat()})
    return (pd.DataFrame(patients), pd.DataFrame(events),
            pd.DataFrame(visits), pd.DataFrame(aes))


def gen_marketing(studies: pd.DataFrame):
    """Lead-gen campaigns (Meta Lead Ads style) with daily spend + leads."""
    campaigns, daily = [], []
    cid = 0
    channels = ["Meta", "Google", "Programmatic", "Community Outreach"]
    for _, st in studies.iterrows():
        for _ in range(int(rng.integers(2, 5))):
            cid += 1
            campaign_id = f"CMP-{cid:04d}"
            c_start = date.fromisoformat(st["start_date"]) + timedelta(days=int(rng.integers(0, 60)))
            length = int(rng.integers(45, 200))
            channel = rng.choice(channels)
            campaigns.append({"campaign_id": campaign_id, "study_id": st["study_id"],
                              "channel": channel, "geo": rng.choice(REGIONS),
                              "start_date": c_start.isoformat()})
            for d in range(length):
                day = c_start + timedelta(days=d)
                if day > TODAY:
                    break
                spend = float(np.round(rng.uniform(50, 900), 2))
                leads = int(max(0, rng.poisson(spend / rng.uniform(40, 120))))
                daily.append({"campaign_id": campaign_id, "study_id": st["study_id"],
                              "activity_date": day.isoformat(), "channel": channel,
                              "spend_usd": spend, "impressions": int(spend * rng.uniform(40, 120)),
                              "clicks": int(leads * rng.uniform(3, 9)), "leads": leads})
    return pd.DataFrame(campaigns), pd.DataFrame(daily)


def gen_financial(studies: pd.DataFrame, sites: pd.DataFrame):
    budgets, site_costs, invoices = [], [], []
    for _, st in studies.iterrows():
        budgets.append({"study_id": st["study_id"], "currency": "USD",
                        "total_budget_usd": float(st["target_enrollment"]) * rng.uniform(9000, 16000)})
        # monthly site operating costs for active sites on this study
        active_sites = sites.sample(n=int(rng.integers(6, 18)), random_state=int(rng.integers(0, 1e6)))
        start = date.fromisoformat(st["start_date"])
        n_months = min(18, max(1, _daterange(start, TODAY) // 30))
        for _, site in active_sites.iterrows():
            for m in range(n_months):
                month = (start + timedelta(days=30 * m)).replace(day=1)
                site_costs.append({"study_id": st["study_id"], "site_id": site["site_id"],
                                   "month": month.isoformat(),
                                   "operating_cost_usd": float(np.round(rng.uniform(3000, 12000), 2)),
                                   "per_visit_cost_usd": float(np.round(rng.uniform(150, 600), 2))})
        for inv in range(int(rng.integers(3, 9))):
            invoices.append({"invoice_id": f"INV-{st['study_id']}-{inv:03d}", "study_id": st["study_id"],
                             "sponsor": st["sponsor"],
                             "amount_usd": float(np.round(rng.uniform(20000, 250000), 2)),
                             "milestone": rng.choice(["startup", "enrollment", "interim", "closeout"]),
                             "status": rng.choice(["paid", "pending", "overdue"], p=[0.7, 0.22, 0.08]),
                             "invoice_date": (start + timedelta(days=int(rng.integers(10, 400)))).isoformat()})
    return pd.DataFrame(budgets), pd.DataFrame(site_costs), pd.DataFrame(invoices)


def main():
    studies = gen_studies()
    sites = gen_sites()
    patients, events, visits, aes = gen_patients_and_funnel(studies, sites)
    campaigns, mkt_daily = gen_marketing(studies)
    budgets, site_costs, invoices = gen_financial(studies, sites)

    outputs = {
        "studies": studies, "sites": sites, "patients": patients,
        "funnel_events": events, "visits": visits, "adverse_events": aes,
        "campaigns": campaigns, "marketing_daily": mkt_daily,
        "study_budgets": budgets, "site_costs": site_costs, "invoices": invoices,
    }
    for name, df in outputs.items():
        path = LANDING / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"  landing/{name}.csv  ({len(df):,} rows)")
    print(f"Synthetic source extracts written to {LANDING}")


if __name__ == "__main__":
    main()
