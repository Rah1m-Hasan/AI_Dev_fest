# Upay AI Financial Coach

> A hackathon concept prototype for DIU CPC × upay AI Hackathon / AI DEV FEST 2026. **It uses synthetic demo data only and is not an official production upay service.**

Upay AI Financial Coach turns a balance into an understandable financial picture: where money went, what may happen next, and which user-controlled action could be helpful. It does not approve lending, execute transfers, determine eligibility, or provide guaranteed financial outcomes.

## Problem and solution

People can see a wallet balance but often cannot connect it to spending behavior, recurring commitments, month-end pressure, or a realistic savings plan. The prototype joins transaction intelligence, deterministic analytics, interpretable forecasting and a grounded language layer into a single coaching experience.

```mermaid
flowchart LR
  React[React + Vite] --> API[FastAPI REST API]
  API --> PG[(Postgres / SQLAlchemy)]
  API --> A[Analytics & ML-style statistics]
  A --> C[Structured financial context]
  C --> G[Groq explanation]
  G --> F[Validated response / fallback]
  F --> React
```

## Features implemented

- Demo login for student, salaried worker, freelancer and small-business personas.
- Dashboard with live API-backed balance, cash flow, category/weekly charts, health score, forecast, transactions and calculated insight.
- Transaction search and authenticated, stored user category correction feedback.
- Deterministic category aggregation, comparison, recurring expense detection and unusual-expense signals.
- Signature “why did I run out?” evidence calculation before a Groq/fallback explanation.
- Personalized—not 50/30/20—budget recommendation and user-controlled accept/update workflow.
- Savings goals with remaining amount, weekly/monthly contribution, cash-flow feasibility and alternatives.
- 7–30 day rolling-average plus recurring-payment cash-flow forecast.
- Explainable 0–100 informational Financial Health Score, explicitly not a credit score.
- Grounded AI Coach, reports, relevant learning cards, low-budget alerts and behavior-relevant offer explanation.
- Mobile-responsive fintech UI with loading/error/fallback states.

## Why AI is used

Deterministic services handle accounting, balances, percentage changes, budgets, goal math and score computation. Interpretable statistical logic handles forecast/pattern signals. Groq only translates precomputed structured evidence into respectful, concise explanations and never receives database credentials or raw schema dumps. A deterministic response is returned on absent/failed Groq calls.

## Stack

React, TypeScript, Vite, Recharts, Lucide; Python, FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL-compatible configuration, NumPy; optional Groq REST integration. The local quick-start defaults to SQLite for judge reliability; Docker Compose provisions PostgreSQL.

## Data and models

The synthetic generator uses a fixed seed and realistic high-level patterns: salary/irregular income cycles, utility/subscription recurrences, transport, food, groceries, weekend variation and deliberate student month-end pressure. No actual upay information is used or implied. Current seed data contains four demo users and roughly 90 days of activity each; the generator can be scaled for offline experiments.

Public dataset research is in [docs/data-sources.md](docs/data-sources.md). PaySim is recorded as a reviewed reference only—not downloaded or redistributed—because third-party distribution terms must be reconfirmed. The complete data policy is in [data/README.md](data/README.md).

Core tables: `users`, `accounts`, `transactions`, `budgets`, `savings_goals`, `notifications`, and `category_feedback`. The normalized schema is deliberately compact for the working demo; adapter-ready services leave room for merchant/profile/conversation/offer-preference tables in a governed integration.

## Run locally

Prerequisites: Python 3.11+ and Node 20+. PostgreSQL is optional for the quick demo.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # leave DATABASE_URL empty/SQLite default for quick demo, or set PostgreSQL
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`; FastAPI OpenAPI is `http://localhost:8000/docs`.

For PostgreSQL:

```bash
docker compose up db -d
export DATABASE_URL='postgresql+psycopg://upay:upay@localhost:5432/upay_coach'
cd backend && uvicorn app.main:app --reload --port 8000
```

The lifespan bootstrap creates the schema and seeds deterministic data. An initial Alembic migration artifact is provided in `backend/alembic`; production should expand its generated operations and run it in CI rather than relying on the demo bootstrap.

## Environment

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | No for quick demo | PostgreSQL SQLAlchemy URL; SQLite fallback is local only |
| `GROQ_API_KEY` | No | Server-side only optional explanation API key |
| `GROQ_MODEL` | No | Groq model name |
| `JWT_SECRET_KEY` | Yes outside demo | Token signing secret |
| `FRONTEND_URL` | Yes outside demo | CORS allowlist source |
| `ENVIRONMENT` | No | Deployment mode marker |

Never put a server secret in `VITE_*` frontend variables or commit `.env`.

## Test and build

```bash
cd backend && pytest -q
cd frontend && npm run build
```

Tests cover authentication/authorization, calculated analytics, run-out evidence and fallback, budget, goal math, forecasting, health-score bounds, and invalid input. Results should be reported only after running them in the target environment.

## Demo accounts

- `demo.student@upay.local` — Arif; designed to demonstrate rising food/transport pressure.
- `demo.salary@upay.local` — Nadia; regular salary cycle.
- `demo.freelancer@upay.local` — Samiha; variable income.

No password is needed for the explicit demo selector.

## API surface

All API routes are under `/api/v1`. Key groups are `auth`, `dashboard`, `transactions`, `analytics`, `coach`, `budgets`, `goals`, `forecast`, `financial-health`, `reports`, `alerts`, `learning`, `offers`, plus `health` and `system/status`. See [docs/api.md](docs/api.md) and `/docs` for executable schemas.

## Responsible AI, privacy and security

All figures are marked as historical calculated values, forecasts, or AI/fallback explanations. Important output includes supporting evidence and optional actions. User control is explicit: budgets/goals are saved only by user request; offers are relevance-scoped; category corrections are feedback. Inputs are validated, ORM queries are parameterized, JWT guards every personal endpoint, chat length is capped, CORS is explicit, and Groq failures use a bounded timeout/fallback. More: [docs/privacy.md](docs/privacy.md), [docs/ai-design.md](docs/ai-design.md).

## Evaluation and limitations

See [docs/evaluation.md](docs/evaluation.md) for metrics and no-invented-results policy. This is a synthetic, seed-data prototype: forecast accuracy is not validated against real customers; the frontend does not yet include a full Bangla translated UI; alert persistence and per-user offer preferences are minimal; Alembic needs generated production operations; and gateway rate limiting/audit controls are deployment work.

## Future controlled upay integration

A future `UpayTransactionProvider` would replace the `SyntheticTransactionProvider` only after user consent, data-minimization/governance approval, anonymization where appropriate, API access, threat modeling and security review. It must remain a user-assistance product, not a consequential decision engine.

## 2–4 minute judging flow

1. Select **Arif · Student** and open the dashboard.
2. Show calculated category/weekly spending and Financial Health (not credit) score.
3. Open **AI Coach** → “Why is my balance low?”; inspect grounded evidence and fallback/provider badge.
4. Open **Budget**, accept the personalized plan; it saves via API.
5. Open **Goals**, create a fund and view feasibility/alternatives.
6. Open **Reports** and then **Offers** to show useful context rather than pushy marketing.

## Team and disclosure

Team members: add names before submission. External libraries/services: FastAPI, SQLAlchemy, React, Vite, Recharts, Lucide, optional Groq, optional PostgreSQL. Public dataset research disclosure is above. Live URL: _to be deployed_. Screenshots: _add from the running demo before submission_.
