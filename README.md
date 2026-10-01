# Vireo Audio Support Analytics

This project builds a Streamlit dashboard to help Priya Raman identify support agents who need review or training and estimate the operational business impact.

## What is included
- Streamlit dashboard for CSAT, response time, SLA breach, replacement cost, and agent-level alerts.
- Pre-built analysis logic for corrected legacy timestamps, Tier-1 vs Tier-2 comparison, and quality checks.
- Validation tests that confirm the critical calculations.
- A business memo and a completed submission form for the take-home brief.

## Setup
1. Open a terminal in this folder.
2. Install the dependencies:
   pip install -r requirements.txt
3. Start the dashboard:
   streamlit run app.py

## Data assumptions
- `agent_id` is always the join key; names are not used for analysis.
- Blank CSAT is treated as no response and excluded from averages.
- Legacy tickets use UTC in `resolved_at`; the analysis converts them to IST before calculating handle time.
- SLA targets are: chat 15 minutes, voice 2 hours, social 4 hours, email 8 hours.
- Replacement cost uses: product unit cost + ₹340 logistics.
- `replacement_issued = Y` plus a refund is treated as a policy exception and flagged.

## Run the validation tests
pytest -q

## Notes
- No paid AI API calls are used. The dashboard uses deterministic rule-based logic, which keeps the cost well below the client’s internal threshold.
- The review list is tier-aware and intentionally uses a minimum sample size to avoid noisy rankings.
