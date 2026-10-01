from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CHANNEL_SLA_MINUTES = {
    "chat": 15,
    "voice": 120,
    "social": 240,
    "email": 480,
}
LEGACY_UTC_OFFSET = pd.Timedelta(hours=5, minutes=30)
REPLACEMENT_LOGISTICS_INR = 340
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "Data"


def _data_path(base_dir: str | Path, suffix: str) -> Path:
    base = Path(base_dir)
    matches = list(base.glob(f"*{suffix.lstrip('-')}"))
    if len(matches) == 0:
        raise FileNotFoundError(f"Could not locate a file ending with {suffix!r} in {base}")
    return matches[0]


def prepare_ticket_data(data_dir: str | Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    base = Path(data_dir).resolve()
    tickets_path = _data_path(base, "-tickets.csv")
    products_path = _data_path(base, "-products.csv")
    agents_path = _data_path(base, "-agents.csv")

    tickets = pd.read_csv(tickets_path, parse_dates=["created_at", "first_response_at", "resolved_at"])
    products = pd.read_csv(products_path)
    agents = pd.read_csv(agents_path)

    tickets = tickets.merge(products[["sku", "unit_cost_inr"]], left_on="product_sku", right_on="sku", how="left")
    tickets = tickets.merge(agents[["agent_id", "team", "tier", "site", "shift"]], on="agent_id", how="left")

    tickets["resolved_at_corrected"] = tickets["resolved_at"]
    legacy_mask = tickets["source_system"].eq("legacy_fd")
    tickets.loc[legacy_mask, "resolved_at_corrected"] = (
        pd.to_datetime(tickets.loc[legacy_mask, "resolved_at"]) + LEGACY_UTC_OFFSET
    )

    tickets["first_response_minutes"] = (
        pd.to_datetime(tickets["first_response_at"]) - pd.to_datetime(tickets["created_at"])
    ).dt.total_seconds() / 60
    tickets["handle_hours"] = (
        pd.to_datetime(tickets["resolved_at_corrected"]) - pd.to_datetime(tickets["first_response_at"])
    ).dt.total_seconds() / 3600
    tickets["sla_breach"] = tickets.apply(
        lambda row: pd.isna(row["first_response_at"]) or (
            row["channel"] in CHANNEL_SLA_MINUTES and row["first_response_minutes"] > CHANNEL_SLA_MINUTES[row["channel"]]
        ),
        axis=1,
    )
    tickets["replacement_cost"] = np.where(
        tickets["replacement_issued"].eq("Y"), tickets["unit_cost_inr"].fillna(0) + REPLACEMENT_LOGISTICS_INR, 0.0
    )
    tickets["csat_score"] = pd.to_numeric(tickets["csat_score"], errors="coerce")
    tickets["replacement_issued"] = tickets["replacement_issued"].fillna("N")

    tickets["ticket_month"] = tickets["created_at"].dt.to_period("M").astype(str)
    tickets["quarter"] = tickets["created_at"].dt.to_period("Q").astype(str)
    return tickets


def compute_agent_summary(
    tickets: pd.DataFrame,
    agents: pd.DataFrame | None = None,
    data_dir: str | Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    if agents is None:
        agents = pd.read_csv(_data_path(Path(data_dir), "-agents.csv"))

    merged = tickets.merge(agents[["agent_id", "team", "tier", "site", "shift"]], on="agent_id", how="left")
    all_counts = merged.groupby("agent_id").size().rename("total_tickets")

    csat = merged[merged["csat_score"].notna()].groupby("agent_id").agg(
        n_csat=("csat_score", "size"),
        avg_csat=("csat_score", "mean"),
        median_csat=("csat_score", "median"),
    )

    operational = merged.groupby("agent_id").agg(
        median_handle_hours=("handle_hours", "median"),
        mean_handle_hours=("handle_hours", "mean"),
        sla_breach_rate=("sla_breach", "mean"),
        replacement_rate=("replacement_issued", lambda s: (s.eq("Y")).mean()),
        replacement_cost_total=("replacement_cost", "sum"),
        refund_rate=("refund_amount_inr", lambda s: s.notna().mean()),
    )

    summary = all_counts.to_frame().join(csat).join(operational)
    summary = summary.reset_index().rename(columns={"index": "agent_id"})
    summary["tier"] = summary["agent_id"].map(
        agents.set_index("agent_id")["tier"].to_dict()
    )
    summary["team"] = summary["agent_id"].map(
        agents.set_index("agent_id")["team"].to_dict()
    )
    summary["site"] = summary["agent_id"].map(
        agents.set_index("agent_id")["site"].to_dict()
    )
    summary["shift"] = summary["agent_id"].map(
        agents.set_index("agent_id")["shift"].to_dict()
    )
    summary["n_csat"] = summary["n_csat"].fillna(0)
    summary["avg_csat"] = summary["avg_csat"].fillna(np.nan)
    return summary.sort_values(["tier", "avg_csat", "n_csat"], ascending=[True, True, False], na_position="last")


def get_review_agents(agent_summary: pd.DataFrame, tier: str | int | None = None, min_csat_n: int = 15) -> pd.DataFrame:
    pool = agent_summary[agent_summary["n_csat"] >= min_csat_n].copy()
    if tier is not None:
        pool = pool[pool["tier"].astype(str).str.contains(str(tier), na=False)]
    if pool.empty:
        return pool
    return pool.sort_values(["avg_csat", "n_csat"], ascending=[True, False]).reset_index(drop=True)


def compute_business_impact(
    tickets: pd.DataFrame,
    agents: pd.DataFrame | None = None,
    data_dir: str | Path = DEFAULT_DATA_DIR,
) -> dict:
    if agents is None:
        agents = pd.read_csv(_data_path(Path(data_dir), "-agents.csv"))

    last_quarter = tickets["created_at"].dt.to_period("Q").max()
    replacement_df = tickets[tickets["replacement_issued"].eq("Y")].copy()
    quarterly_spend = replacement_df[replacement_df["quarter"].eq(str(last_quarter))]["replacement_cost"].sum()
    review_agents = get_review_agents(
        compute_agent_summary(tickets, agents, data_dir=data_dir),
        min_csat_n=15,
    ).head(10)
    review_ids = set(review_agents["agent_id"].tolist())
    review_spend = tickets[
        tickets["agent_id"].isin(review_ids) & tickets["replacement_issued"].eq("Y") & tickets["quarter"].eq(str(last_quarter))
    ]["replacement_cost"].sum()
    estimated_reduction_percent = 0.15
    estimated_savings = review_spend * estimated_reduction_percent
    return {
        "quarter": str(last_quarter),
        "quarterly_cost_inr": float(quarterly_spend),
        "review_quarter_cost_inr": float(review_spend),
        "review_agent_ids": sorted(review_ids),
        "estimated_reduction_percent": float(estimated_reduction_percent * 100),
        "estimated_savings_inr": float(estimated_savings),
    }
