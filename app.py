from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from vireo_support.analysis import compute_agent_summary, compute_business_impact, prepare_ticket_data

DATA_DIR = Path(__file__).resolve().parent / "Data"


@st.cache_data
def load_clean_data() -> pd.DataFrame:
    return prepare_ticket_data(DATA_DIR)


@st.cache_data
def load_agents() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "agents.csv")


st.set_page_config(page_title="Vireo Audio Support Analytics", layout="wide")
st.title("Vireo Audio Support Analytics")
st.caption("Built from the Vireo ticket exports and policy rules. All metrics exclude blank CSAT and correct legacy UTC timestamps before analysis.")

tickets = load_clean_data()
agents = load_agents()
agent_summary = compute_agent_summary(tickets, agents)
impact = compute_business_impact(tickets, agents, DATA_DIR)

overview = tickets[tickets["csat_score"].notna()]
monthly_csat = overview.groupby(overview["created_at"].dt.to_period("M").astype(str))["csat_score"].mean().reset_index()
monthly_csat.columns = ["month", "avg_csat"]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Overall CSAT", f"{overview['csat_score'].mean():.2f}/5")
with col2:
    st.metric("Median handle time", f"{overview['handle_hours'].median():.1f} hrs")
with col3:
    st.metric("SLA breach rate", f"{tickets['sla_breach'].mean() * 100:.1f}%")
with col4:
    st.metric("Replacement cost (18 mo)", f"₹{tickets['replacement_cost'].sum():,.0f}")

st.subheader("Overall CSAT and trend")
chart = px.line(monthly_csat, x="month", y="avg_csat", markers=True, title="Monthly CSAT trend")
chart.update_yaxes(range=[2.5, 4.5])
st.plotly_chart(chart, use_container_width=True)

st.subheader("Key operational metrics")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Avg handle time", f"{overview['handle_hours'].mean():.1f} hrs")
with metric_col2:
    st.metric("Median response time", f"{(overview['first_response_minutes'].median() / 60):.2f} hrs")
with metric_col3:
    st.metric("Tickets with replacement", f"{(tickets['replacement_issued'] == 'Y').sum():,}")
with metric_col4:
    st.metric("Quarterly replacement spend", f"₹{impact['quarterly_cost_inr']:,.0f}")

st.subheader("Channel and team comparison")
channel_summary = tickets.groupby("channel").agg(
    ticket_count=("ticket_id", "size"),
    csat=("csat_score", lambda s: s.dropna().mean() if s.notna().any() else np.nan),
    sla_breach_rate=("sla_breach", "mean"),
    median_handle_hours=("handle_hours", "median"),
)
team_summary = tickets.groupby("team").agg(
    agent_count=("agent_id", "nunique"),
    csat=("csat_score", lambda s: s.dropna().mean() if s.notna().any() else np.nan),
    replacement_rate=("replacement_issued", lambda s: s.eq("Y").mean()),
    sla_breach_rate=("sla_breach", "mean"),
)
st.dataframe(channel_summary, use_container_width=True)
st.dataframe(team_summary, use_container_width=True)

st.subheader("Bottom 10 review list")
# separate Tier 1 and Tier 2, because the warranty rotation is intentionally harder.
review_tables = []
for tier_label, tier_value in [("Tier 1", 1), ("Tier 2", 2)]:
    subset = agent_summary[(agent_summary["tier"] == tier_value) & (agent_summary["n_csat"] >= 15)].sort_values("avg_csat").head(10)
    if not subset.empty:
        subset = subset[["agent_id", "team", "site", "tier", "n_csat", "avg_csat", "median_csat", "median_handle_hours", "sla_breach_rate", "replacement_rate"]]
        review_tables.append((tier_label, subset))

for label, table in review_tables:
    st.markdown(f"### {label}")
    st.dataframe(table, use_container_width=True)

st.subheader("Business-impact estimate")
review_rate = tickets[tickets["replacement_issued"].eq("Y")].shape[0] / len(tickets)
review_cost = impact["review_quarter_cost_inr"]
st.write(
    "Targeted retraining should focus on the lowest 10 agents in comparable cohorts. "
    "The data indicates that the review cohort accounts for about "
    f"₹{review_cost:,.0f} in replacement spend in the most recent quarter and a 15% reduction would save "
    f"about ₹{impact['estimated_savings_inr']:,.0f} per quarter."
)

st.subheader("Data quality and validation")
quality_df = pd.DataFrame(
    {
        "check": [
            "Negative handle-time records",
            "Legacy UTC to IST correction applied",
            "Blank CSAT excluded from averages",
            "Refund + replacement combo flagged",
            "Junk IVR transcripts ignored as data quality",
        ],
        "result": [
            str(int((tickets["handle_hours"] < 0).sum())),
            "Yes",
            f"{tickets['csat_score'].notna().sum():,} responses",
            str(int(((tickets["refund_amount_inr"].notna()) & (tickets["replacement_issued"].eq("Y"))).sum())),
            "Yes",
        ],
    }
)
st.dataframe(quality_df, use_container_width=True)

st.code(
    "\n".join([
        "Key assumptions:",
        "- Join on agent_id, never name.",
        "- Blank CSAT = no response, not zero.",
        "- Legacy tickets: resolved_at is UTC, converted to IST before handle-time calculation.",
        "- Replacement cost = unit_cost_inr + ₹340 logistics.",
    ])
)

st.caption("AI usage: no paid API calls were used; the analysis stays deterministic and policy-driven to keep cost under control.")
