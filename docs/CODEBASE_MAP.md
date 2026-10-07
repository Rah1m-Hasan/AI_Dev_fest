# Codebase map

Upay AI Financial Coach is a React/Vite single-page app backed by FastAPI. It
uses synthetic data and must retain a deterministic financial/AI fallback when
Groq is unavailable.

| Area | Location | Notes |
| --- | --- | --- |
| Application shell and routes | `frontend/src/App.tsx` | All browser routes and navigation layout. |
| Screen implementations | `frontend/src/pages.tsx`, `frontend/src/components/` | Page-level experiences are grouped by feature (`coach`, `goals`, `health`, `insights`, `learn`, `offers`, `people`). |
| Frontend API/types | `frontend/src/api/client.ts`, `frontend/src/types.ts` | `/api/v1` client and shared response shapes. |
| Formatting/explanations | `frontend/src/format.ts`, `frontend/src/metricExplanation.ts` | Keep money/date presentation and explain-metric navigation consistent. |
| API surface | `backend/app/main.py` | FastAPI app and stable `/api/v1` contracts. |
| Database | `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/db.py`, `backend/alembic/` | Do not delete migrations or make destructive schema changes during cleanup. |
| Financial calculations | `backend/app/services/analytics_service.py`, `safe_to_spend_service.py`, `income_adaptive_service.py` | Calculations are deterministic and are the source of truth. |
| Assistant/AI | `backend/app/services/groq_service.py`, `assistant_action_service.py`, `intent_service.py` | Groq is optional; preserve fallback and confirmation flows. |
| Feature services | `backend/app/services/` | Goals/plans, learning/offers, recipients, trusted people/helpers, and transaction drafts. |
| Synthetic demo data | `backend/app/services/seed.py` | Reproducible personas and transactions. |

## Main routes

`/`, `/coach`, `/coach/insights`, `/coach/plan`, `/coach/goals`,
`/coach/scenario`, `/coach/assistant`, `/coach/reports`, `/coach/learn`,
`/coach/transactions`, `/offers`, `/people`, and `/trusted-helper`.

## Checks

```bash
cd frontend && npm test && npm run build
cd backend && python -m pytest
```

Ignore generated local output (`frontend/node_modules`, `frontend/dist`, Python
bytecode and test caches). Recreate frontend dependencies with `npm ci`.
