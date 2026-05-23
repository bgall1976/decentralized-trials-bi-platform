"""
Data-quality tests over the Gold layer. These are the assertions a senior engineer wires into CI
so a broken transform fails the build rather than silently corrupting a leadership report.
"""
import pandas as pd


def test_core_tables_nonempty(gold):
    for t in ["dim_study", "dim_site", "dim_patient", "fact_patient_enrollment",
              "kpi_overview", "kpi_predictability_forecast"]:
        assert len(gold(t)) > 0, f"{t} is empty"


def test_enrollment_pk_unique(gold):
    f = gold("fact_patient_enrollment")
    assert not f.duplicated(subset=["patient_id", "study_id"]).any(), "duplicate patient-study grain"
    assert f["patient_id"].notna().all() and f["study_id"].notna().all()


def test_referential_integrity(gold):
    f, studies, sites = gold("fact_patient_enrollment"), gold("dim_study"), gold("dim_site")
    assert set(f["study_id"]).issubset(set(studies["study_id"])), "orphan study_id in fact"
    assert set(f["site_id"]).issubset(set(sites["site_id"])), "orphan site_id in fact"


def test_funnel_monotonicity(gold):
    """A patient can't be enrolled without having been consented first (Faster/Predictable rely on this)."""
    f = gold("fact_patient_enrollment")
    enrolled = f[f["is_enrolled"]]
    assert enrolled["consented_date"].notna().all(), "enrolled patients missing consent"
    bad = enrolled.dropna(subset=["consented_date", "enrolled_date"])
    assert (pd.to_datetime(bad["enrolled_date"]) >= pd.to_datetime(bad["consented_date"])).all()


def test_screen_fail_rate_in_range(gold):
    c = gold("kpi_predictability_conversion")
    assert c["screen_fail_rate_pct"].between(0, 100).all(), "screen-fail rate out of [0,100]"


def test_diversity_percentages_sum_per_study(gold):
    d = gold("kpi_accessibility_diversity")
    sums = d.groupby("study_id")["pct_of_study_enrolled"].sum()
    assert sums.between(95, 105).all(), f"diversity % per study should ~100, got\n{sums}"


def test_forecast_fields_present(gold):
    fc = gold("kpi_predictability_forecast")
    for col in ["projected_completion_date", "on_track", "weekly_velocity", "pct_to_target"]:
        assert col in fc.columns
    assert fc["on_track"].dtype == bool


def test_accessibility_decentralized_share_valid(gold):
    o = gold("kpi_overview")
    assert o["pct_decentralized_enrolled"].dropna().between(0, 100).all()
