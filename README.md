# UPAY AI ASSIST

> A hackathon concept prototype for DIU CPC × upay AI Hackathon / AI DEV FEST 2026. **It uses synthetic demo data only and is not an official production upay service.**

**upay handles money. AI Assist helps people understand, plan, and act on it more confidently.**

UPAY AI ASSIST is a **concept integration prototype** for an intelligence layer inside the familiar upay experience. It helps a customer understand what changed, decide whether an action fits their current context, prepare that action in natural language, and confirm it themselves. It is not an official upay product, replacement wallet, autonomous financial agent, lending system, or production payment integration.

The demo starts on a compact upay-style home, adds **AI Financial Coach** as a service entry, and demonstrates integration points in History, Account/Financial Health, and Offers without claiming access to a production upay API.

## Problem and solution

People can see a wallet balance but often cannot connect it to spending behavior, recurring commitments, month-end pressure, or a realistic savings plan. The prototype joins transaction intelligence, deterministic analytics, interpretable forecasting and a grounded language layer into a single coaching experience.

```mermaid
flowchart LR
    A[User]
    B[Upay-style Interface]
    C[AI Assist]
    D[Intent + Context Layer]
    E[Deterministic Financial Engine]
    F[Structured Evidence]
    G[AI Explanation]
    H[Review & Confirmation]
    I[Simulated Action]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
```

## Product architecture

```mermaid
flowchart LR
  Home[Existing upay experience] --> Today[Your Money Today]
  Home --> Assist[AI Assist service tile]
  Assist --> Understand[Understand]
  Understand --> Decide[Decide]
  Decide --> Act[Prepare action]
  Act --> Confirm[User confirms + PIN]
```

Mobile navigation stays focused on Pulse, Insights, Plan, and Coach. Transactions, Reports, Learn, and Relevant Savings are secondary destinations. Desktop uses the same hierarchy in a compact shell.

## Four hero capabilities

1. **AI Assist** — understands English, Bangla, and mixed-language requests; presents grounded answers and stays useful with a deterministic fallback if Groq is unavailable.
2. **Safe-to-Spend + Money Runway** — shows an estimated flexible amount after known bills, a savings commitment and reserve, plus a clearly labelled runway projection.
3. **Intent-to-Action** — resolves a person, builds a financial-context transfer draft, then requires `DRAFT → REVIEWED → CONFIRMED → PIN_VERIFIED → COMPLETED`.
4. **Guided Mode + People, not numbers** — provides a calmer, larger-step workflow and contact cards with human trust labels rather than opaque scores.

Secondary tools remain available under **Plan**, **Insights**, and **More** so they support the core journey rather than compete with it.

## Features implemented

- Demo login for student, salaried worker and freelancer personas.
- Upay-style host home with AI Assist as a normal service tile and one compact “Your Money Today” section.
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
- Conversational, task-oriented AI Assist with suggested actions for sending money, affordability, spending changes, saving, runway and trusted people.
- Server-side recipient resolution with a human-readable relationship label, masked phone number, and an ambiguity response instead of guessing.
- Simulated transfer review, explicit confirmation and user-entered PIN. The AI never sends money silently.
- Dense monthly reports, behavior-triggered learning and transaction-derived relevant savings with opt-in control.
- Mobile-responsive fintech UI with loading/error/fallback states.

## Signature intelligence

- **Money Pulse:** combines spending comparison, upcoming recurring activity, runway and buffer logic into a neutral status with inspectable drivers.
- **Money Runway:** simulates balance against recent daily spending, observed income timing and a conservative buffer.
- **Safe-to-Save:** subtracts forecast spending and a safety buffer, caps the result by prorated recent savings capacity, and returns a range rather than false precision.
- **What Changed:** compares equal rolling 30-day windows and ranks category changes by impact.
- **Money Story:** derives income, unusual purchase, category-change, recurring-payment and net-cash-flow events.
- **Scenario Lab:** reuses forecast and goal math for reversible what-if comparisons.

## Deterministic engine vs AI layer

The deterministic backend handles balances, transaction totals, category comparisons, recurring costs, Safe-to-Spend, savings feasibility, runway, scenarios, recipient records and transaction state. AI Assist only interprets natural language, extracts an intent/entities, explains provided evidence, and asks for clarification when needed. Groq only translates precomputed structured evidence into respectful, concise explanations and never receives database credentials or raw schema dumps. A deterministic response is returned on absent/failed Groq calls.

The UI’s concise disclosure is intentional: **AI explains the result; it does not calculate the balance, move money, or access a PIN.**

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

All demo accounts use password: `password`

| Email | Persona | Description |
|-------|---------|-------------|
| `demo.student@upay.local` | Student (Arif) | Rising food/transport pressure, month-end balance challenges |
| `demo.salary@upay.local` | Salaried Worker (Nadia) | Regular salary cycle, stable expenses |
| `demo.freelancer@upay.local` | Freelancer (Samiha) | Variable income, irregular cash flow |
| `demo.business@upay.local` | Business Owner (Rafi) | Small business owner, higher transaction volume |

## API surface

All API routes are under `/api/v1`. Key groups are `auth`, `dashboard`, `transactions`, `analytics`, `coach`, `budgets`, `goals`, `forecast`, `financial-health`, `reports`, `alerts`, `learning`, `offers`, plus `health` and `system/status`. See [docs/api.md](docs/api.md) and `/docs` for executable schemas.

## Responsible AI, privacy and security

All figures are marked as historical calculated values, forecasts, or AI/fallback explanations. Important output includes supporting evidence and optional actions. User control is explicit: budgets/goals are saved only by user request; offers are relevance-scoped; category corrections are feedback. Inputs are validated, ORM queries are parameterized, JWT guards every personal endpoint, chat length is capped, CORS is explicit, and Groq failures use a bounded timeout/fallback. More: [docs/privacy.md](docs/privacy.md), [docs/ai-design.md](docs/ai-design.md).

## Prototype validation and limitations

See [docs/evaluation.md](docs/evaluation.md) for metrics and the no-invented-results policy. Validation is currently **deterministic scenario tests**, including intent/entity extraction, recipient resolution, Safe-to-Spend reconciliation, invalid transaction-state rejection, and no direct `DRAFT → COMPLETED` transition. Product evaluation should measure intent classification, recipient/amount extraction, ambiguity detection, key-flow completion, normal vs Guided Mode steps, and time-to-answer; no real-user percentages are claimed.

This is a synthetic, seed-data prototype: forecast accuracy is not validated against real customers; the frontend does not yet include a full Bangla translated UI; chat history is session-local; offer preferences are demonstrated but not persisted in a production preference store; and production migrations, gateway rate limiting and audit controls remain deployment work. The frontend bundle should be route-split before production delivery.

## Future controlled upay integration

A future `GovernedUpayTransactionProvider` would replace the current `SyntheticTransactionProvider` behind the same analytics boundary only after user consent, data-minimization/governance approval, anonymization where appropriate, API access, threat modeling and security review. The intelligence services, evidence contracts and human-control boundaries remain provider-independent. It must remain a user-assistance product, not a consequential decision engine.

## Recommended 2-minute judging flow

1. Select **Arif · Student** and stay on the familiar upay-style Home. Point out the normal **AI Assist** tile and the three “Your Money Today” answers.
2. Open **AI Assist** and ask: “Why am I running short this month?” Show the calculated food/transport evidence and concise explanation.
3. Ask: “Rafi ke 2000 taka pathabo.” AI Assist resolves **Rafi Ahmed**, shows his relationship/trust context, balance after, Safe-to-Spend impact and estimated runway change.
4. Tap **Review transfer**, then **Confirm**. Show that neither action has moved money yet.
5. Enter the simulated PIN yourself, show the success message and return Home to show the updated balance/Safe-to-Spend.
6. If time allows, open **Guided Mode** or **People, not numbers** to show the accessibility and safety layer.

An optional in-product Demo Tour introduces the same product logic without forcing it on every session.

## Team and disclosure

**Team:** Hasib (Team Leader)

**External Libraries/Services:**
- Backend: FastAPI, SQLAlchemy 2, Pydantic, Python-Jose, Passlib
- Frontend: React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide
- AI: Groq API (qwen/qwen3.8-27b model) - optional, falls back to deterministic
- Database: SQLite (local dev) / PostgreSQL (production)
- Docker: PostgreSQL 16 Alpine

**Public Dataset Research Disclosure:** PaySim mobile-money simulator was reviewed as a reference but not used. See [docs/data-sources.md](docs/data-sources.md) for full details.

**Live URL:** _to be deployed_

**Screenshots:** _add from the running demo before submission_

## Hackathon Compliance

- **Theme:** upay AI Financial Coach Challenge
- **All data is synthetic** — no real upay API, no real user data
- **No real money transfers** — all transactions are simulated
- **AI explains calculated results** — does not calculate balances or move funds
- **User always confirms** — PIN verification required for any action
- **Privacy-first** — minimal data collection, synthetic demo only
