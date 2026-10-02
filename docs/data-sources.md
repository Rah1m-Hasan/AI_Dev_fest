# Data source and privacy review

| Dataset | Source | License | Records | Useful for | Used? |
|---|---|---|---:|---|---|
| PaySim mobile-money simulator | [official GitHub](https://github.com/EdgarLopezPhD/PaySim) | GPL-3.0 for simulator; verify Kaggle distribution separately | Public release commonly documented as 6.36M | Mobile-money transaction schema/reference | No raw data; reference only |
| UCI Individual Household Electric Power Consumption | [UCI](https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption) | Terms need confirmation for redistribution | 2,075,259 | Time-series forecasting methodology only; not transaction data | No |
| Upay AI Coach synthetic demo | Repository generator | Project license | 4 users / ~90 days each at seed time | End-to-end financial coaching demo | Yes |

## Decision

Research found PaySim to be relevant and synthetic, but its public full CSV is large and commonly distributed through Kaggle. Its simulator is GPL-3.0, and the raw distribution's exact reuse terms should be checked at the download point. The prototype therefore does not download or redistribute it. UCI household power data is an open forecasting benchmark but is not financial transaction data, so it is not used.

The independently generated data is safer for a public hackathon demo: it contains no PII, asserts no relationship to upay production data, and can be regenerated with a fixed seed. It is intentionally a behavioral simulation, not a representation of Bangladeshi customers.
