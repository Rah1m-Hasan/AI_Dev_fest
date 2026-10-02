# Evaluation plan

No real-world success claims are made.

| Component | Current validation | Future metric |
|---|---|---|
| Categorization | Deterministic merchant/category mapping; user correction stored | Accuracy and macro-F1 on a held-out labelled synthetic/public-safe test set |
| Forecast | Rolling 60-day daily average plus recurring detection | MAE/MAPE against a time-ordered holdout |
| Budget | Tests ensure positive limits, constrained savings target and category figures | Constraint satisfaction, feasibility and user accept/modify/reject rates |
| Goal planner | Tests ensure exact remaining amount and infeasible alternative list | Feasibility against observed free cash flow |
| Health score | Deterministic/reproducible component tests | Reproducibility and explanation coverage |
| Coach | Tests verify calculated evidence and fallback response | Factual-grounding evaluation; number-match rate |

For a pilot, measure budget adherence, goal completion, reduction in unexpected low-balance days, weekly active coach users, and accepted/rejected recommendations. Keep train/validation/test data time-separated and never tune on the test split.
