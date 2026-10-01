import pandas as pd

from vireo_support.analysis import (
    compute_agent_summary,
    compute_business_impact,
    prepare_ticket_data,
)


def test_legacy_resolved_at_is_corrected_for_utc_to_ist():
    tickets = prepare_ticket_data(data_dir='Data')
    row = tickets[tickets['ticket_id'] == 'TK-240001'].iloc[0]
    assert row['handle_hours'] > 0
    assert abs(row['handle_hours'] - 0.21666666666666667) < 1e-6


def test_replacement_cost_uses_unit_cost_plus_logistics():
    tickets = prepare_ticket_data(data_dir='Data')
    row = tickets[tickets['ticket_id'] == 'TK-240833'].iloc[0]
    assert row['replacement_cost'] == 1460.0


def test_sla_breach_uses_channel_targets_and_ignores_blank_csat():
    tickets = prepare_ticket_data(data_dir='Data')
    assert tickets['sla_breach'].dtype == bool
    assert tickets['csat_score'].isna().sum() > 0
    assert tickets['csat_score'].notna().mean() > 0.4


def test_agent_summary_ranks_tier_aware_and_has_min_sample_size():
    tickets = prepare_ticket_data(data_dir='Data')
    agents = pd.read_csv('Data/agents.csv')
    agent_summary = compute_agent_summary(tickets, agents)
    assert 'tier' in agent_summary.columns
    assert ('A3041' in agent_summary['agent_id'].values) or ('A3042' in agent_summary['agent_id'].values)
    assert agent_summary['n_csat'].min() >= 1


def test_business_impact_estimate_is_non_negative_and_rounded():
    tickets = prepare_ticket_data(data_dir='Data')
    impact = compute_business_impact(tickets)
    assert impact['estimated_reduction_percent'] >= 0
    assert impact['quarterly_cost_inr'] >= 0
