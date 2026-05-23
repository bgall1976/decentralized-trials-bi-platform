"""
Leadership dashboard — organized around the mission: Faster, More Predictable, More Accessible.

Reads the Gold layer (Parquet) directly via DuckDB. Run with:  streamlit run bi/dashboard/app.py
(after `make generate && make run`). This mirrors what the Power BI semantic model serves in prod.
"""
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st
import plotly.express as px

GOLD = Path(__file__).resolve().parents[2] / "data" / "gold"

st.set_page_config(page_title="Decentralized Trials BI", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return duckdb.connect().execute(
        f"SELECT * FROM read_parquet('{GOLD / (name + '.parquet')}')"
    ).df()


if not (GOLD / "kpi_overview.parquet").exists():
    st.error("Gold layer not found. Run `make generate && make run` first.")
    st.stop()

st.title("Decentralized Trials — Leadership Dashboard")
st.caption("Making clinical trials **faster, more predictable, and more accessible.** "
           "Every view below maps to one of those goals.")

overview = load("kpi_overview")
studies = sorted(overview["study_id"].unique())
picked = st.sidebar.multiselect("Studies", studies, default=studies)
ov = overview[overview["study_id"].isin(picked)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Studies", len(ov))
c2.metric("Enrolled to date", int(ov["enrolled_to_date"].sum()))
c3.metric("On track", f"{int(ov['on_track'].sum())} / {len(ov)}")
c4.metric("Avg cost / enrolled", f"${ov['cost_per_enrolled_usd'].mean():,.0f}")

faster, predictable, accessible = st.tabs(["⏱ Faster", "📈 More Predictable", "🌍 More Accessible"])

with faster:
    st.subheader("Speed: where time is won or lost")
    speed = load("kpi_speed_study")
    speed = speed[speed["study_id"].isin(picked)]
    a, b = st.columns(2)
    a.plotly_chart(px.bar(speed, x="study_id", y="days_to_first_patient",
                          title="Days to first patient enrolled", color="therapeutic_area"),
                   use_container_width=True)
    b.plotly_chart(px.bar(speed, x="study_id", y="avg_days_lead_to_enrolled",
                          title="Avg days: lead → enrolled"), use_container_width=True)
    wk = load("kpi_speed_site_weekly")
    wk = wk[wk["study_id"].isin(picked)]
    trend = wk.groupby("week_start", as_index=False)["enrolled_in_week"].sum()
    st.plotly_chart(px.line(trend, x="week_start", y="enrolled_in_week",
                            title="Weekly enrollment velocity (all selected studies)", markers=True),
                    use_container_width=True)

with predictable:
    st.subheader("Predictability: will we hit target, and when?")
    fc = load("kpi_predictability_forecast")
    fc = fc[fc["study_id"].isin(picked)]
    st.dataframe(fc[["study_id", "enrolled_to_date", "target_enrollment", "pct_to_target",
                     "weekly_velocity", "projected_completion_date", "planned_end_date", "status"]],
                 use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    a.plotly_chart(px.bar(fc, x="study_id", y=["enrolled_to_date", "target_enrollment"],
                          barmode="group", title="Enrolled to date vs target"),
                   use_container_width=True)
    conv = load("kpi_predictability_conversion")
    conv = conv[conv["study_id"].isin(picked)]
    b.plotly_chart(px.bar(conv, x="study_id", y="screen_fail_rate_pct",
                          title="Screen-fail rate (%)"), use_container_width=True)

with accessible:
    st.subheader("Accessibility: reaching more — and more representative — patients")
    div = load("kpi_accessibility_diversity")
    div = div[div["study_id"].isin(picked)]
    by_race = div.groupby("race_ethnicity", as_index=False)["enrolled"].sum()
    a, b = st.columns(2)
    a.plotly_chart(px.pie(by_race, names="race_ethnicity", values="enrolled",
                          title="Enrolled by race / ethnicity"), use_container_width=True)
    reach = load("kpi_accessibility_reach")
    by_type = reach.groupby("site_type", as_index=False)["enrolled"].sum()
    b.plotly_chart(px.bar(by_type, x="site_type", y="enrolled",
                          title="Enrolled by site type (community + mobile = decentralized reach)",
                          color="site_type"), use_container_width=True)
    st.plotly_chart(px.bar(ov, x="study_id", y="pct_decentralized_enrolled",
                           title="% of enrollment via decentralized (community/mobile) sites"),
                    use_container_width=True)
