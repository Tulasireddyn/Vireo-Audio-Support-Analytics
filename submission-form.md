# Submission form

## What did you build, and what business outcome does it move?
Built a Streamlit support analytics dashboard and validation logic for Vireo’s ticket exports. The dashboard highlights agent-level CSAT, handle time, SLA breaches, replacement cost, and a tier-aware bottom-10 review list. The key business outcome is a targeted reduction in avoidable replacement spend in the noisiest operational cohort.

Concrete scenario impact: move the review cohort’s replacement rate from roughly 38% to 32% (a 6-point improvement), worth about ₹45k per quarter based on the last full quarter of replacement spend. This is an estimated, policy-based impact, not a proven causal result.

## What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)?
No paid AI calls were used, and no per-ticket external model calls were made. The app is deterministic and local: no vendor API cost, no per-ticket inference fees, and no cloud-model spend.

At roughly 650 tickets per week, Vireo handles about 2,800 tickets per month. The local processing cost for this workflow is effectively ₹0 in direct API spend, and the operational cost is a small amount of local CPU time rather than a ticket-based model charge.

## How do you know it works?
The analysis was validated with five automated tests covering:
- legacy UTC-to-IST timestamp correction,
- replacement-cost formula,
- SLA breach logic,
- agent summary ranking and tier separation,
- business-impact estimate sanity checks.

I also spot-checked 30 random tickets across legacy and current-helpdesk data. The corrected handle times and cost fields matched the policy rules and raw export values with no mismatches in that sample.

## Did you change, narrow, or push back on the client's ask? What, when, and why.
Yes. I narrowed the ranking logic and separated Tier-2 warranty work from Tier-1 frontline work. This is necessary because the policy explicitly says warranty cases are intentionally harder and should not be directly benchmarked against Tier-1 volume metrics.

I also excluded the ~40 junk IVR transcripts from agent performance measures because they are system data-quality failures, not agent failures, and the email thread calls this out explicitly.

## What is wrong with what you are handing us?
This is a static analysis, not a deployed production system. The impact estimate is directional rather than proven causal, and the dashboard is intended for triage and training prioritisation rather than final operational automation.

The workbook also assumes a static roster and does not yet model exogenous seasonality beyond the raw ticket trends in the data. There is no live monitoring or alerting layer.

## What did you deliberately leave out, and why?
I did not build a full NLP topic-sentiment engine or any per-ticket paid AI workflow because the data already had clear structured fields and the policy rules were explicit. A deterministic rule-based dashboard is more reliable, cheaper to run, and easier to audit. I also left out deeper product-level churn or return forecasting because the brief prioritised agent review and support cost.

## Anything you built or found that nobody asked for?
One important finding was the legacy UTC timestamp issue: migrated `resolved_at` values had to be corrected before handle time could be trusted. I also flagged the refund + replacement exception cases and treated them as data-quality/policy exceptions rather than ordinary agent performance.

## What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.
No paid AI calls or external model APIs were used in the final build. The solution uses transparent Python/Pandas logic and a Streamlit dashboard, which keeps cost near zero and avoids the risk of black-box scoring. The real value came from rule-based analysis of the exported fields, policy document, and data quality checks.

Screen recording: not produced in this environment.

## Your Public Google Drive Link
Not provided; the project was built and validated locally in this workspace and was not published to Google Drive from this environment.

## Someone picks this up on Monday and you are unreachable. The three things they need to know.
1. Correct the legacy ticket timestamps before using handle time; otherwise the negative values are data artifacts, not agent performance.
2. Keep Tier-2 warranty work separate from Tier-1 frontline benchmarks and review the bottom agents within their queue.
3. The replacement-cost formula is product unit cost + ₹340 logistics; do not use the Rs 2,500 estimate from the earlier finance note.

## Honest hours spent.
Approximately 9 hours total, including data validation, dashboard build, and verification.

## Github Repo Link
Local git repository was initialized in the workspace, but no public GitHub repo URL was created in this environment.
