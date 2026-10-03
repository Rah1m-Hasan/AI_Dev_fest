# Upay AI Financial Coach

> A hackathon concept prototype for DIU CPC × upay AI Hackathon / AI DEV FEST 2026. **It uses synthetic demo data only and is not an official production upay service.**

Upay AI Financial Coach is a **concept integration prototype** for a future intelligence layer inside upay. Upay already tells a user what happened; the coach helps explain why it happened, forecast what may happen next, and simulate realistic options before the user decides. It does not approve lending, execute transfers, determine eligibility, or provide guaranteed financial outcomes.

The demo starts on a compact upay-style home, adds **AI Financial Coach** as a service entry, and demonstrates integration points in History, Account/Financial Health, and Offers without claiming access to a production upay API.

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

## Product architecture

```mermaid
flowchart LR
  Home[upay-style Home] --> Coach[AI Financial Coach]
  History[History + Smart Insights] --> Coach
  Coach --> Pulse[Pulse: understand now]
  Coach --> Insights[Insights: explain why]
  Coach --> Plan[Plan: budget and goals]
  Coach --> Chat[Coach: grounded conversation]
  Plan --> Scenario[Scenario Lab: explore options]
  Scenario --> Decision[User decides]
```

Mobile navigation stays focused on Pulse, Insights, Plan, and Coach. Transactions, Reports, Learn, and Relevant Savings are secondary destinations. Desktop uses the same hierarchy in a compact shell.

## Features implemented

- Demo login for student, salaried worker and freelancer personas.
- Upay-style host home with a clearly marked AI Financial Coach entry point.
- Flagship Pulse with API-backed balance, cash flow, Money Pulse, Money Runway, Safe-to-Save, What Changed, upcoming activity, Money Story and recent transactions.
- Transaction search and authenticated, stored user category correction feedback.
- History tabs for Transaction Details, Transaction Summary and Smart Insights, plus transaction-level AI context.
- Deterministic category aggregation, comparison, recurring expense detection and unusual-expense signals.
- Signature “why did I run out?” evidence calculation before a Groq/fallback explanation.
- Personalized—not 50/30/20—budget recommendation with accept, customize, reset, validation and explainability.
- A three-step savings-goal flow with contribution requirement, cash-flow feasibility and scenario-linked alternatives.
- Timing-aware forecasting: regular income follows its observed monthly cycle; irregular income is conservatively discounted.
- Scenario Lab with before/after projected balance, safe-to-save change and goal-contribution impact. Scenarios never mutate account data.
- Explainable 0–100 informational Financial Health Score, explicitly not a credit score.
- Conversational grounded AI Coach with real input, send/Enter, history, loading and error states, suggested questions, follow-up actions and a human-readable evidence drawer.
- Dense monthly reports, behavior-triggered learning and transaction-derived relevant savings with opt-in control.
- Mobile-responsive fintech UI with loading/error/fallback states.

## Signature intelligence

- **Money Pulse:** combines spending comparison, upcoming recurring activity, runway and buffer logic into a neutral status with inspectable drivers.
- **Money Runway:** simulates balance against recent daily spending, observed income timing and a conservative buffer.
- **Safe-to-Save:** subtracts forecast spending and a safety buffer, caps the result by prorated recent savings capacity, and returns a range rather than false precision.
- **What Changed:** compares equal rolling 30-day windows and ranks category changes by impact.
- **Money Story:** derives income, unusual purchase, category-change, recurring-payment and net-cash-flow events.
- **Scenario Lab:** reuses forecast and goal math for reversible what-if comparisons.

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

Open `http://localhost:5173`; FastAPI OpenAPI is `http://localhost:8000/docs`. Vite proxies `/api` to the backend in development, so embedded previews do not call a hard-coded browser-side API localhost address.

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
cd backend && pytest -q tests/test_core.py
cd backend && python -m compileall -q app
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run build
```

`npm run test` intentionally aliases the TypeScript typecheck; Vitest is not installed, so this project does not claim a passing browser unit-test suite. Browser behavior is verified against the running app at the documented mobile, tablet and desktop viewports.

The portable core suite covers authentication, calculated analytics, Safe-to-Save reconciliation/capping, budget JSON persistence, goal math, forecasting, health-score bounds and scenario non-mutation. On the current Python 3.14 environment it passes **9 tests**. The retained async API contract suite is skipped on Python 3.14 because the installed Starlette/AnyIO in-process transport can deadlock; run it normally on Python 3.11–3.13. On Python 3.14, start Uvicorn and use live authenticated HTTP checks as the contract evidence. The final live sweep verifies all three profiles across dashboard, intelligence, spending, transactions, budgets, goals, forecast, health, reports, learning, offers, Coach and all four scenario types.

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

See [docs/evaluation.md](docs/evaluation.md) for metrics and no-invented-results policy. This is a synthetic, seed-data prototype: forecast accuracy is not validated against real customers; the frontend does not yet include a full Bangla translated UI; chat history is session-local; offer preferences are demonstrated but not persisted in a production preference store; and production migrations, gateway rate limiting and audit controls remain deployment work. The frontend bundle should be route-split before production delivery.

## Future controlled upay integration

A future `GovernedUpayTransactionProvider` would replace the current `SyntheticTransactionProvider` behind the same analytics boundary only after user consent, data-minimization/governance approval, anonymization where appropriate, API access, threat modeling and security review. The intelligence services, evidence contracts and human-control boundaries remain provider-independent. It must remain a user-assistance product, not a consequential decision engine.

## 2–4 minute judging flow

1. Select **Samiha · Freelancer** and begin on the upay-style Home.
2. Tap **AI Financial Coach** and show Money Pulse, Money Runway and the conservative Safe-to-Save range.
3. Open **What Changed**, then ask Coach: “Why is my balance lower?”
4. Open **See evidence** to show the period, transaction count, comparison, largest driver and recurring costs.
5. Ask: “What if I spend ৳500 less per week?” The grounded fallback shows the full 30-day impact.
6. Open **Scenario Lab** to compare current and changed projections side by side.
7. Open the savings goal to discuss feasibility, then finish on the monthly report and Money Story.

An optional in-product Demo Tour introduces the same product logic without forcing it on every session.

## Team and disclosure

Team members: add names before submission. External libraries/services: FastAPI, SQLAlchemy, React, Vite, Recharts, Lucide, optional Groq, optional PostgreSQL. Public dataset research disclosure is above. Live URL: _to be deployed_. Screenshots: _add from the running demo before submission_.
