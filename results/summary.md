# IT Helpdesk SLA Analytics - Observed Results

> Synthetic demonstration data for 2025. Not a client engagement or production service desk.

## Headline metrics

| Metric | Observed value |
| --- | --- |
| Total tickets | 480 |
| Closed tickets | 396 |
| Open / pending backlog | 84 |
| Critical backlog | 8 |
| First-response SLA (%) | 82.50 |
| Resolution SLA (%) | 77.50 |
| Average first response (minutes) | 182 |
| Median resolution (hours) | 15.30 |
| Reopened rate among closed (%) | 8.60 |
| Average CSAT (1-5) | 3.68 |
| CSAT responses | 308 |
| Resolved tickets | 396 |

## SLA by priority

| priority | tickets | response_sla_pct | resolution_sla_pct | avg_resolution_hours |
| --- | --- | --- | --- | --- |
| Low | 153 | 78.40 | 76.70 | 39.70 |
| Medium | 199 | 85.40 | 73.50 | 20.90 |
| High | 87 | 82.80 | 84.70 | 5.70 |
| Critical | 41 | 82.90 | 84.80 | 3 |

## SLA by category

| category | tickets | response_sla_pct | resolution_sla_pct | avg_csat |
| --- | --- | --- | --- | --- |
| Software | 129 | 80.60 | 72.10 | 3.55 |
| Hardware | 102 | 79.40 | 87.10 | 3.91 |
| Network | 83 | 85.50 | 80 | 3.78 |
| Access | 81 | 85.20 | 72.20 | 3.56 |
| Email | 66 | 86.40 | 78.80 | 3.60 |
| Other | 19 | 73.70 | 69.20 | 3.40 |

## Top five agents by ticket volume

| agent | tickets | closed | resolution_sla_pct | avg_csat |
| --- | --- | --- | --- | --- |
| Agent Rivera | 92 | 75 | 74.70 | 3.59 |
| Agent Campos | 85 | 67 | 80.60 | 3.61 |
| Agent Neira | 83 | 72 | 70.80 | 3.80 |
| Agent Solis | 81 | 69 | 84.10 | 3.75 |
| Agent Quispe | 75 | 63 | 85.70 | 3.88 |

## Last six months

| month | tickets | closed | response_breaches | resolution_breaches | response_sla_pct | resolution_sla_pct | avg_csat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-07 | 40 | 34 | 7 | 9 | 82.50 | 73.50 | 3.84 |
| 2025-08 | 32 | 25 | 7 | 6 | 78.10 | 76 | 3.43 |
| 2025-09 | 40 | 34 | 4 | 4 | 90 | 88.20 | 3.62 |
| 2025-10 | 31 | 26 | 4 | 5 | 87.10 | 80.80 | 3.71 |
| 2025-11 | 43 | 33 | 10 | 4 | 76.70 | 87.90 | 3.85 |
| 2025-12 | 39 | 31 | 4 | 5 | 89.70 | 83.90 | 3.96 |

## Reading notes

- The lowest resolution-SLA category with at least 30 tickets is Software at 72.1%.
- First-response SLA is measured on all tickets; an unanswered open ticket counts as a breach.
- Resolution SLA is measured only on tickets with a resolution timestamp.
- CSAT is the mean of available 1-5 satisfaction responses, not a percentage.
- Durations use 24/7 calendar time, not business hours.
- The 90% line in the charts is a visual reference for this demo, not a contractual target.
