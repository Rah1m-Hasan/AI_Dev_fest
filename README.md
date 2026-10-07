# Upay AI Financial Coach

> **upay handles money; AI Assist helps people understand, plan, and act on it more confidently.**

Upay AI Financial Coach is an AI-powered financial guidance and assisted-action prototype designed for the **DIU CPC × upay AI Hackathon / AI DEV FEST 2026**. It demonstrates how an intelligence layer could complement an MFS experience by helping customers understand their financial behavior, plan more confidently, and complete actions through guided conversational workflows.

---

> **This project is a concept prototype developed for the DIU CPC × upay AI Hackathon / AI DEV FEST 2026. It uses synthetic demo data only and is not an official production upay service. No real upay customer data is used. No real financial transactions are executed.**

---

## Team Ora 3 Jon

| Role | Name |
|---|---|
| **Captain** | Hasibul Hasan Rahim |
| Member | Fuad Al Abid |
| Member | Abu Zubayer Ahmmed |

---

## Live Deployment

**Frontend:** https://ai-dev-fest.vercel.app  
**Backend API:** https://backend-kappa-sooty-49.vercel.app

Demo login: `demo.student@upay.local` / `password`

---

## Problem Statement

MFS users in Bangladesh can perform transactions, but often lack context and guidance about:

- where their money actually goes each month;
- why their balance changed unexpectedly;
- how much they can safely spend without affecting upcoming obligations;
- how long their available balance will last given spending patterns;
- whether a purchase fits their current financial situation;
- realistic savings goals they can actually achieve;
- how to navigate complicated financial workflows with confidence;
- accessible support when elderly or less digitally confident family members need help.

Existing apps show balances and transaction history. They do not help users understand the story behind the numbers or guide them through confident action.

---

## Proposed Solution

Upay AI Financial Coach acts as an **intelligence and assistance layer** inside an MFS-style experience. The conceptual workflow is:

```
USER INPUT
    ↓
DETERMINISTIC FINANCIAL ANALYTICS
    ↓
AI INTERPRETATION / CONVERSATION
    ↓
GUIDANCE
    ↓
USER CONFIRMATION
    ↓
ACTION
```

AI assists the user at every step, while important financial calculations and controls remain **deterministic** — calculated from actual transaction data, not invented by a language model.

### Core Product Philosophy

- **Understand** — Help users see spending patterns, financial pressure, and the story behind their balance.
- **Plan** — Help users set realistic savings goals and budget targets based on their actual cash flow.
- **Act** — Help users complete financial workflows through guided conversational interaction.
- **Confirm** — Every important financial action requires explicit user confirmation before anything is simulated or executed.

---

## Implemented Features

### AI Financial Coach
- Conversational financial guidance in English, Bangla, and mixed language
- Intent detection and entity extraction from natural language
- AI-powered explanations grounded in calculated financial evidence
- Deterministic fallback when Groq is unavailable
- Suggested actions based on user's financial context

### Financial Intelligence
- **Money Pulse** — One clear signal summarizing financial health with inspectable drivers
- **Money Runway** — Days remaining on current balance at recent spending pace
- **Safe-to-Spend** — Amount available after committed expenses and safety buffer
- **Safe-to-Save** — Week-by-week savings feasibility range
- **Financial Health Score** — Explainable 0–100 score (not a credit score)
- **Money Story** — Auto-derived events: income, unusual purchases, category changes, recurring payments
- **Personal Spending Forecast** — Lightweight Random Forest estimates for next-7-day and next-30-day spending
- **Financial Risk Classification** — Lightweight Random Forest `LOW`/`MEDIUM`/`HIGH` liquidity-stress signal, with a deterministic fallback

### Spending & Transactions
- Transaction history with category labels
- Spending breakdown by category (deterministic aggregation)
- Comparison with previous period (30-day rolling windows)
- Recurring expense detection
- Unusual expense signals
- Category correction feedback (stored for learning)

### Planning & Savings
- Personalized budget recommendation (not 50/30/20 — based on actual cash flow)
- Savings goals with contribution plan and deadline feasibility check
- Cash flow forecasting with timing-aware income cycles
- Scenario Lab for reversible what-if comparisons (does not mutate account data)

### Intent-to-Action (Send Money)
- Natural language intent recognition ("Send 500 to Fuad")
- Server-side recipient resolution with ambiguity detection (never guesses)
- Relationship context labels (Trusted / Known / Needs verification)
- Transfer draft with full financial impact preview (balance after, runway change, fee)
- Explicit confirmation step before PIN entry
- Demo PIN verification (simulated execution — no real money moves)
- State machine: DRAFT → REVIEWED → CONFIRMED → PIN_VERIFIED → COMPLETED

### People, Not Numbers
- Trusted contacts with relationship history
- Human-readable trust labels instead of opaque scores
- Guided Mode for calm, larger-step workflows
- Trusted Helper Mode for assisted access by family members

### Reporting & Learning
- Weekly and monthly financial reports
- Behavior-triggered micro-learning lessons
- Personalized offer recommendations (opt-in, relevance-scoped)

### Accessibility
- Mobile-responsive fintech UI
- Sidebar navigation with tooltip mode
- Guided Mode for users who prefer step-by-step flows
- Loading, error, and fallback states throughout

---

## Prototype / Partial Features

- AI chat history is session-local (not persisted across sessions)
- Frontend Bangla translated UI is demonstrated but not fully complete
- Offer preferences are demonstrated but not yet persisted in a production preference store

---

## Planned / Future Features

- Full Bangla UI translation
- Persisted chat history
- Production upay API integration (behind `GovernedUpayTransactionProvider`)
- PostgreSQL production deployment with managed database
- Route-splitting for production frontend bundle
- Full-text search for transactions
- Push notifications

---

## AI Role — What AI Actually Does

### AI / Groq Layer

Used for:

- Intent interpretation from natural language queries
- Conversational financial guidance
- Translating calculated financial evidence into accessible natural language
- Simplifying complex financial information
- Generating context-aware suggested actions

### Deterministic Financial Layer

Used for:

- Balance calculations and transaction arithmetic
- Safe-to-spend and safe-to-save calculations
- Financial health scoring
- Savings feasibility computations
- Budget recommendations based on actual cash flow
- Transaction validation and state transitions
- Recipient resolution and relationship classification
- Cash flow forecasting with observed income timing
- All confirmation and PIN verification logic

### Why AI Is Needed

The AI component converts **structured financial evidence** and application state into accessible guidance and conversational workflows. The application does **not** rely on an LLM to invent financial facts. AI interprets and explains evidence produced by deterministic systems. The Groq API key is server-side only and optional — a full deterministic fallback always works.

### Financial Safety Boundary

> **AI explains the result; it does not calculate the balance, move money, or access a PIN.**

No AI service participates in transaction execution or PIN verification.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│         React + Vite Frontend               │
│                                              │
│  Home | AI Assist | Pulse | Transactions |  │
│  People | Guided Actions | Reports | Goals  │
└──────────────────────┬──────────────────────┘
                       │
                       │ /api/v1
                       ▼
┌─────────────────────────────────────────────┐
│           FastAPI Backend                    │
│                                              │
│  Auth │ Services │ Analytics │ AI Coach     │
└─────────────┬─────────────────┬──────────────┘
              │                 │
              ▼                 ▼
       SQLAlchemy 2         Groq API
       (SQLite /           (optional
        PostgreSQL)         fallback exists)
```

### Architecture Principles

- API-driven, frontend/backend separation
- Deterministic calculations separate from LLM-generated responses
- Evidence-first AI: Groq explains, it does not calculate
- Environment-based configuration via environment variables
- Synthetic demo data only
- Human confirmation required for consequential actions
- PIN verification is application-side only (never sent to AI)

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI |
| ORM | SQLAlchemy 2 |
| Local Database | SQLite |
| Production Database | PostgreSQL (via Docker Compose) |
| AI | Groq API (`llama-3.3-70b-versatile` or `qwen/qwen3.8-27b`) — optional with deterministic fallback |
| Authentication | JWT (HMAC-SHA256, demo tokens) |
| Charts | Recharts |
| Icons | Lucide React |
| Testing | pytest |
| ML | scikit-learn Random Forests + joblib (CPU-only, optional) |

---

## Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + all routes
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── db.py             # Database engine + session
│   │   ├── api/deps.py       # JWT authentication dependency
│   │   ├── core/config.py    # Environment variable settings
│   │   └── services/
│   │       ├── analytics_service.py   # Deterministic financial calculations
│   │       ├── groq_service.py        # AI explanation with fallback
│   │       ├── intent_service.py      # Intent detection
│   │       ├── safe_to_spend_service.py
│   │       ├── transaction_draft_service.py  # Intent-to-Action state machine
│   │       ├── recipient_service.py    # Contact resolution
│   │       ├── relationship_service.py # Relationship classification
│   │       ├── seed.py         # Synthetic demo data generator
│   │       └── ...
│   ├── tests/
│   │   ├── test_core.py      # Core deterministic tests
│   │   └── test_api_contracts.py
│   ├── alembic/              # Database migrations
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React app + routing
│   │   ├── pages.tsx        # Page components
│   │   ├── api/client.ts    # API client
│   │   ├── components/
│   │   │   ├── coach/       # CoachPanel, PIN modal, coach components
│   │   │   ├── people/      # People/contacts pages
│   │   │   └── ui.tsx       # Shared UI components
│   │   ├── styles.css       # Tailwind + custom CSS
│   │   └── ...
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── privacy.md
│   ├── ai-design.md
│   ├── evaluation.md
│   └── data-sources.md
├── .env.example
├── .gitignore
├── vercel.json
├── docker-compose.yml
├── README.md
└── CLAUDE.md
```

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Backend |
| Node.js | 20+ | Frontend |
| npm | 10+ | Package manager |
| Git | any recent | Version control |
| PostgreSQL | 16 | Production only |
| Docker | latest | Optional for PostgreSQL |
| Groq API key | — | Optional; fallback always works |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No (dev) | `sqlite:///./upay_demo.sqlite3` | PostgreSQL or SQLite connection string |
| `GROQ_API_KEY` | Optional | _(empty)_ | Groq API key for live AI explanations |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model name |
| `JWT_SECRET_KEY` | Production | `demo-only-change-me` | Secret for JWT signing; **must change in production** |
| `FRONTEND_URL` | No (dev) | `http://localhost:5173` | CORS allowlist origin |
| `ENVIRONMENT` | No | `development` | `development` or `production` |

> Never put secret values in `.env` files that are committed to version control. Use `.env.example` as a template.

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Rah1m-Hasan/AI_Dev_fest.git
cd AI_Dev_fest
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add GROQ_API_KEY if you have one (optional)
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
```

---

## Running Locally

### Start the Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Train the optional ML models

```bash
cd backend
python -m app.ml.train_models
```

This creates compact local joblib artifacts and `app/ml/models/model_metrics.json`. The dashboard's **AI Financial Forecast** section shows only these saved, real holdout metrics. If the artifacts are absent, the app keeps using deterministic forecasts and safety calculations.

### View saved model evaluation

```bash
cd backend
python -m json.tool app/ml/models/model_metrics.json
```

- API running at: http://localhost:8000
- Swagger docs at: http://localhost:8000/docs

### Start the Frontend

```bash
cd frontend
npm run dev
```

- Frontend at: http://localhost:5173

### Demo Login Credentials

All demo accounts use password: `password`

| Email | Persona |
|---|---|
| `demo.student@upay.local` | Arif (Student) — month-end pressure |
| `demo.salary@upay.local` | Nadia (Salaried) — stable income |
| `demo.freelancer@upay.local` | Samiha (Freelancer) — variable income |

---

## Running with PostgreSQL (Production Path)

```bash
# Start PostgreSQL with Docker
docker compose up db -d

# Run backend with PostgreSQL
export DATABASE_URL='postgresql+psycopg://upay:upay@localhost:5432/upay_coach'
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Build Commands

### Frontend Production Build

```bash
cd frontend
npm run build
```

Output is in `frontend/dist/`.

### Backend Validation

```bash
cd backend
python -m compileall -q app
```

---

## API Reference

**Base URL:** `/api/v1`

### Health

```
GET /api/v1/health
```

### Authentication

```
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### Dashboard

```
GET /api/v1/dashboard/summary
```

### Transactions

```
GET /api/v1/transactions
GET /api/v1/transactions/{id}
GET /api/v1/transactions/categories
GET /api/v1/transactions/summary
PATCH /api/v1/transactions/{id}/category
POST /api/v1/transactions/check-impact
```

### Analytics

```
GET /api/v1/analytics/spending
GET /api/v1/analytics/cashflow
GET /api/v1/analytics/merchants
GET /api/v1/analytics/recurring
GET /api/v1/analytics/comparison
```

### AI Assistant (primary conversational entry point)

```
POST /api/v1/assistant/message
POST /api/v1/assistant/actions/{id}/confirm
POST /api/v1/assistant/actions/{id}/authorize  # PIN stays outside the LLM
DELETE /api/v1/assistant/actions/{id}
```

`/assistant/message` is the UI's single conversational endpoint. It uses Groq
for validated routing and grounded wording when configured, then falls back to
deterministic intent handling and templates without exposing provider errors.
The older coach routes below remain for backwards compatibility.

### Legacy AI Coach routes

```
POST /api/v1/coach/chat
POST /api/v1/coach/run-out-analysis
GET  /api/v1/coach/insights
POST /api/v1/coach/parse-intent
GET  /api/v1/coach/safe-to-spend
GET  /api/v1/coach/income-adaptive
```

### Intent-to-Action (Send Money)

```
POST /api/v1/transactions/draft
GET  /api/v1/transactions/draft/active
POST /api/v1/transactions/draft/{id}/review
POST /api/v1/transactions/draft/{id}/confirm
POST /api/v1/transactions/draft/{id}/execute   # requires PIN
DELETE /api/v1/transactions/draft/{id}
```

### Recipients

```
GET  /api/v1/recipients/search?q=
GET  /api/v1/recipients/resolve?q=
GET  /api/v1/trusted-contacts
POST /api/v1/trusted-contacts
DELETE /api/v1/trusted-contacts/{id}
```

### Budgets & Goals

```
GET  /api/v1/budgets/recommendation
GET  /api/v1/budgets/current
POST /api/v1/budgets
PUT  /api/v1/budgets/{id}
GET  /api/v1/goals
POST /api/v1/goals
GET  /api/v1/goals/{id}
GET  /api/v1/goals/{id}/plan
```

### Forecast & Financial Health

```
GET /api/v1/forecast/cashflow
GET /api/v1/forecast/upcoming-expenses
GET /api/v1/financial-health
GET /api/v1/financial-health/history
```

### Reports & Alerts

```
GET /api/v1/reports/weekly
GET /api/v1/reports/monthly
GET /api/v1/alerts
PATCH /api/v1/alerts/{id}/read
```

### Learning & Offers

```
GET  /api/v1/learning/recommended
POST /api/v1/learning/{id}/complete
GET  /api/v1/offers/recommended
PATCH /api/v1/offers/preferences
```

### Scenarios

```
POST /api/v1/scenarios/simulate
```

### Trusted Helpers

```
GET  /api/v1/trusted-helpers
POST /api/v1/trusted-helpers
DELETE /api/v1/trusted-helpers/{id}
POST /api/v1/trusted-helper/request
```

Full OpenAPI schema available at `/docs`.

---

## Important User Flows

### Financial Insight Flow

1. User opens AI Assist
2. Asks: "Why am I running short this month?"
3. System retrieves calculated spending evidence (deterministic)
4. AI explains the patterns in natural language
5. Suggested actions are displayed

### Safe-to-Spend Flow

1. User asks: "Can I safely spend ৳5,000?"
2. System calculates available funds after upcoming obligations
3. AI explains the result with evidence breakdown
4. User decides based on transparent information

### Intent-to-Action Flow (Send Money)

1. User: "Send ৳500 to Fuad"
2. AI Coach parses intent and identifies recipient
3. Transfer draft is prepared with full impact preview:
   - Balance after transfer
   - Safe-to-spend impact
   - Money runway change
   - Transfer fee
4. User reviews the summary
5. User explicitly confirms
6. User enters demo PIN (`1234`)
7. Simulated transfer executes (no real money moves)

---

## Security and Financial Safety

- **No credentials committed to Git** — all secrets via environment variables
- **Synthetic data only** — no production upay customer information
- **Deterministic financial calculations** — AI explains results, does not calculate balances
- **No unrestricted LLM control** — Groq receives structured evidence only, never database credentials
- **Confirmation-gated actions** — every consequential step requires user confirmation
- **PIN never sent to AI** — verification is application-side only
- **JWT authentication** on all personal endpoints
- **CORS restricted** to configured frontend origin
- **Production requires:** HTTPS, secure secret management, PostgreSQL, rate limiting

---

## Responsible AI

### Privacy
All data is synthetic demo data. No real user information is collected or processed.

### Explainability
Financial responses are based on visible calculated evidence. Users can inspect what drove each insight.

### Human Oversight
Consequential actions (send money, budget creation, goal changes) require explicit user confirmation.

### Transparency
Every response clearly distinguishes:
- Deterministic calculations (from actual transaction data)
- AI-generated explanations (from Groq)
- Scenario projections (labeled as estimates, not guarantees)

### No Autonomous Financial Decisions
The prototype never autonomously approves or denies lending, or makes consequential financial decisions on behalf of the user.

---

## Synthetic Data Policy

All demonstration customer, transaction, spending, savings, contact, and financial data used by this prototype is **synthetic** — self-generated for hackathon demonstration purposes.

**No production upay customer data or personally identifiable production customer information is used.**

Synthetic data is generated by `backend/app/services/seed.py` using a fixed seed, producing realistic patterns:
- Salary/irregular income cycles
- Utility and subscription recurrences
- Transport and food spending
- Weekend spending variation
- Deliberate student month-end pressure

Current seed data contains four demo users and approximately 90 days of activity each.

---

## External Services and Components

| Service | Purpose | Type |
|---|---|---|
| **Groq API** | AI explanation and conversation | External API (optional) |
| **React** | UI framework | Open source |
| **Vite** | Build tool | Open source |
| **FastAPI** | Backend framework | Open source |
| **SQLAlchemy 2** | ORM | Open source |
| **Tailwind CSS** | Styling | Open source |
| **Recharts** | Charts | Open source |
| **Lucide React** | Icons | Open source |
| **PostgreSQL** | Production database | Open source |
| **Docker** | Containerization | Open source |

No third-party datasets, templates, or assets are used in this prototype.

---

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/test_core.py -q
```

Current result: **14 tests passing**

### Frontend Type Check

```bash
cd frontend
npm run typecheck
```

### Frontend Build

```bash
cd frontend
npm run build
```

---

## Manual Verification Checklist

- [ ] Frontend opens at http://localhost:5173
- [ ] Demo login works for all three personas
- [ ] Synthetic balance and transactions load on dashboard
- [ ] AI Assist opens and responds to questions
- [ ] Money Pulse, Money Runway, and Safe-to-Spend display correctly
- [ ] Spending breakdown chart renders
- [ ] Transaction history loads with categories
- [ ] Budget recommendation displays
- [ ] Savings goals can be created
- [ ] Send Money flow works end-to-end:
  - [ ] Intent parsing identifies recipient and amount
  - [ ] Draft summary shows balance after, runway impact, fee
  - [ ] Confirmation screen appears before PIN
  - [ ] Demo PIN (`1234`) executes simulated transfer
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] `/docs` API documentation loads

---

## Recommended Demo Flow (2–3 minutes)

1. **Open dashboard** — show the familiar upay-style home with AI Assist tile
2. **Show Money Today** — highlight Safe-to-Spend and Money Runway
3. **Open AI Assist** — ask: "Why am I running short this month?"
4. **Show evidence-based explanation** — highlight that AI explains calculated data
5. **Test Send Money** — ask: "Send ৳500 to Fuad"
6. **Show Intent-to-Action** — reveal draft summary with full financial impact
7. **Confirm and enter PIN** — show `1234`, demonstrate simulated execution
8. **Return to home** — show updated balance and Safe-to-Spend
9. **Optional** — open Guided Mode or Trusted People to show safety/accessibility layers

---

## Live Deployment

**Frontend:** https://ai-dev-fest.vercel.app  
**Backend API:** https://backend-kappa-sooty-49.vercel.app

Demo login: `demo.student@upay.local` / `password`

### Planned Production Architecture

```
Browser
   │
   ▼
Vercel
   │
   ├── React/Vite Frontend (static hosting)
   │
   └── FastAPI Backend (serverless or container)
            │
            ├── PostgreSQL (managed database)
            │
            └── Groq API (AI explanations)
```

### Required Deployment Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GROQ_API_KEY` | Groq API key |
| `JWT_SECRET_KEY` | Secure random secret for JWT signing |
| `FRONTEND_URL` | Deployed frontend URL for CORS |
| `ENVIRONMENT` | `production` |

---

## Local vs Production

| Environment | Database | AI | Authentication |
|---|---|---|---|
| Local | SQLite | Deterministic fallback | Demo JWT |
| Production | PostgreSQL | Groq (optional) | Secure JWT + secrets |

SQLite is intended only for local/demo development. Production uses PostgreSQL via the provided Docker Compose configuration.

---

## Limitations

- **Synthetic data only** — all financial figures are from demo data, not real accounts
- **Hackathon prototype** — not a production-ready application
- **No production upay API** — demonstrates concepts with synthetic data
- **Simulated transactions** — no real money is transferred
- **AI depends on Groq availability** — falls back to deterministic responses when unavailable
- **Session-local chat history** — not persisted across browser sessions
- **Production compliance and security work remains** — see Future Production Path

---

## Future Production Path

1. Governed integration with production MFS systems
2. Production-grade authentication (OIDC/JWT with proper secret management)
3. Secure transaction service integration
4. Regulated approval and risk controls
5. Scalable PostgreSQL infrastructure (managed database)
6. Logging, monitoring, and observability
7. Controlled model evaluation process
8. Security review and penetration testing
9. Privacy and compliance review (BDPA/local regulations)
10. Staged pilot with real users

---

## Hackathon Alignment

**Main Track:** Customer Innovation & Financial Independence

The prototype addresses this through:

- **Financial coaching** — AI-powered explanations of spending and cash flow
- **Savings guidance** — realistic goal-setting based on actual capacity
- **Spending intelligence** — Money Pulse, Safe-to-Spend, and category breakdown
- **Cash-flow awareness** — Runway forecasting and upcoming expense visibility
- **Financial confidence** — guided workflows that explain every step
- **Inclusive conversational UX** — supports Bangla, English, and mixed input; Guided Mode for accessibility

---

## Evaluation Alignment

Without predicting scores, the repository demonstrates:

| Criterion | How Addressed |
|---|---|
| **Problem Relevance** | Real MFS customer friction in financial understanding and action confidence |
| **AI/ML Depth** | AI integrated into interpretation, intent handling, and natural-language assistance; financial calculations remain deterministic |
| **Customer Impact** | Designed to improve financial understanding and reduce anxiety around money management |
| **Prototype Quality** | Working end-to-end product flows with confirmation gates and safety boundaries |
| **Innovation** | Conversational Intent-to-Action with explicit state machine and human confirmation |
| **Scalability** | API-based architecture with PostgreSQL production path and Docker Compose |
| **Responsible AI** | Synthetic data, explainability, confirmation requirements, separation of AI from deterministic accounting |

---

## Contributing

This is a hackathon project. Contributions are limited to the registered team members.

---

## License

This project is a hackathon concept prototype. All rights reserved. Not for commercial use.

---

**DIU CPC × upay AI Hackathon / AI DEV FEST 2026**
