# Upay AI Financial Coach — Project Documentation

> **Upay AI Financial Coach** is a hackathon concept prototype for **DIU CPC × upay AI Hackathon / AI DEV FEST 2026**. It uses **synthetic demo data only** and is **NOT** an official production upay service.

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Demo Users & Personas](#4-demo-users--personas)
5. [Data Models](#5-data-models)
6. [API Endpoints](#6-api-endpoints)
7. [Key Services & Business Logic](#7-key-services--business-logic)
8. [Frontend Structure](#8-frontend-structure)
9. [AI Integration (Groq)](#9-ai-integration-groq)
10. [Authentication](#10-authentication)
11. [Key Workflows](#11-key-workflows)
12. [Configuration](#12-configuration)
13. [Important Constraints](#13-important-constraints)
14. [Quick Start](#14-quick-start)

---

## 1. What It Is

**Upay AI Financial Coach** is an intelligence and assistance layer inside a Mobile Financial Service (MFS) experience. It helps users:

- **Understand** their financial behavior through AI-powered insights
- **Plan** confidently with budget recommendations and savings goals
- **Act** safely through guided conversational workflows (e.g., sending money)
- **Learn** financial literacy through micro-lessons

### Core Philosophy

> **AI explains calculated financial evidence; it does not invent balances, move money, or access PINs. Every consequential action requires explicit human confirmation.**

The system never makes up numbers. Every figure (balance, runway, health score, safe-to-spend) is calculated deterministically in Python. AI only explains what was already calculated. If Groq is unavailable, a deterministic fallback always works.

### Key Screens & Features

| Feature | Description |
|---|---|
| **Money Pulse** | One-line financial health signal with trend |
| **Safe-to-Spend** | How much the user can comfortably spend without hurting goals |
| **Money Runway** | How many days the user can last at their current spending pace |
| **AI Coach** | Conversational interface for financial guidance |
| **Send Money (Intent-to-Action)** | Guided, PIN-confirmed money transfers with AI assistance |
| **Savings Goals** | Create goals, see feasibility analysis, track contributions |
| **Budget Recommendations** | Personalized category limits based on actual spending |
| **Spending Insights** | Category comparisons, recurring detection, unusual expenses |
| **Scenario Lab** | "What if" simulations (purchase, reduce spending, save more, etc.) |
| **Financial Health Score** | 0–100 score across 5 dimensions |
| **Trusted Helpers** | Allow trusted contacts limited, controlled access to your account |
| **Bangla Support** | Explanations available in Bengali (English + Banglish also supported) |

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│                  http://localhost:5173 (dev)                 │
│                  https://upay-ai-demo.vercel.app (prod)      │
└─────────────────────────────┬────────────────────────────────┘
                              │ /api/v1
                              │ JWT Bearer Token
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Uvicorn)                │
│                  http://localhost:8000 (dev)                │
│                      Vercel Functions (prod)                │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌────────────────────────────┐
│   Groq API (optional) │         │   SQLAlchemy 2 ORM        │
│   Deterministic       │         ├────────────────────────────┤
│   fallback always     │         │   SQLite (dev)            │
│   works               │         │   PostgreSQL (prod)        │
└───────────────────────┘         └────────────────────────────┘
```

### Backend Modules

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app — all routes, middleware, CORS, lifespan |
| `app/models.py` | SQLAlchemy 2 ORM models (all database tables) |
| `app/schemas.py` | Pydantic request/response schemas |
| `app/services/analytics_service.py` | Deterministic financial calculations |
| `app/services/groq_service.py` | Groq API integration with fallback |
| `app/services/intent_service.py` | Deterministic intent parsing |
| `app/services/assistant_action_service.py` | Conversational action orchestration |
| `app/services/transaction_draft_service.py` | Send-money state machine |
| `app/services/recipient_service.py` | Contact resolution with ambiguity detection |
| `app/services/relationship_service.py` | Contact classification (trusted/known/new/unusual) |
| `app/services/safe_to_spend_service.py` | Safe-to-spend calculations |
| `app/services/income_adaptive_service.py` | Variable-income analysis |
| `app/services/trusted_helper_service.py` | Trusted helper permissions |
| `app/services/seed.py` | Synthetic demo data generator |

---

## 3. Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool & dev server |
| **TypeScript** | Type safety |
| **React Router v6** | Client-side routing |
| **Axios** | HTTP client |
| **Recharts** | Charts (spending trends, cash flow) |

### Backend

| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **SQLAlchemy 2** | ORM |
| **Pydantic v2** | Data validation |
| **Built-in HMAC-SHA256** | JWT authentication |
| **python-dotenv** | Environment variables |
| **httpx** | HTTP client (Groq calls) |
| **Groq SDK** | AI API client |

### Deployment

| Platform | Component |
|---|---|
| **Vercel** | Frontend (auto-deploys from git) |
| **Vercel Functions** | Backend (Python runtime) |

---

## 4. Demo Users & Personas

All demo users have password: `password`

| Email | Name | Persona | Starting Balance | Financial Story |
|---|---|---|---|---|
| `demo.student@upay.local` | Arif Rahman | Student | ৳10,500 | Month-end pressure; rising food & transport spend near month end |
| `demo.salary@upay.local` | Nadia Islam | Salaried Worker | ৳22,000 | Stable monthly salary; consistent bills and savings |
| `demo.freelancer@upay.local` | Samiha Noor | Freelancer | ৳15,000 | Variable income; irregular but strategic spending |
| `demo.business@upay.local` | Rafi Ahmed | Small Business Owner | ৳30,000 | Business cash flow; higher transaction volume |

### Synthetic Data Generation

The `seed.py` service creates ~90 days of transactions per user using a fixed random seed (`2026`) for reproducibility. It generates:

- **Random merchants** across categories (food, transport, entertainment, bills, shopping, health, education)
- **Recurring bills** (rent, utilities, mobile, subscriptions) on predictable schedules
- **Income deposits** matching each persona's pattern (month-end for students, monthly for salaried, irregular for freelancers/business)
- **Student-specific** month-end multiplier for food/transport (simulates financial pressure near payday)

---

## 5. Data Models

### Core Tables

#### User
```
- id, email, display_name, password_hash
- persona: student | salaried_worker | freelancer | small_business_owner
- preferred_language: en | bn
- created_at, updated_at
```

#### Account
```
- id, user_id, balance (Numeric 14,2), currency (default: BDT)
- account_type, is_primary
```

#### Transaction
```
- id, user_id, account_id, merchant_name, category
- amount, direction: income | expense | transfer_out
- transaction_type: payment | transfer | recharge | bill | topup
- timestamp, balance_before, balance_after
- is_recurring: bool, source: app | self | merchant
- notes, is_flagged
```

#### Budget
```
- id, user_id, total_limit, categories: JSON
- period_type: monthly | weekly, start_date, end_date
- status: active | replaced
```

#### SavingsGoal
```
- id, user_id, name, target_amount, current_amount
- target_date, status: active | paused | completed
- created_at, updated_at
```

#### GoalPlanSettings
```
- id, goal_id, category, saving_preference
- planned_monthly_amount, note
```

#### TrustedContact
```
- id, user_id, name, phone_number
- relationship, nickname, is_trusted: bool
```

#### TrustedHelper
```
- id, user_id, helper_name, relationship, phone
- Permissions (all booleans):
  - can_view_balance, can_view_history
  - can_initiate (always False — helpers cannot act autonomously)
  - can_view_goals, can_view_budget
```

#### TransactionDraft
```
- id, user_id, recipient_id, recipient_name
- amount, fee, state: draft | reviewed | confirmed | completed | cancelled
- created_at, updated_at
```

#### AssistantConversation
```
- id, user_id, messages: JSON
- created_at, updated_at
```

#### AssistantActionDraft
```
- id, conversation_id, action_type
- slots: JSON, state, result: JSON
- created_at, updated_at
```

#### Other Tables
- `Notification`, `CategoryFeedback`, `FinancialLesson`, `UserOfferPreference`, `HelperRequest`, `ChatConversation`, `ChatMessage`

---

## 6. API Endpoints

### Base URL
- **Development**: `http://localhost:8000/api/v1`
- **Production**: Vercel backend URL + `/api/v1`

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login with email → JWT token |
| GET | `/auth/me` | Get current user + balance |

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/summary` | Full financial overview |

### Intelligence

| Method | Endpoint | Description |
|---|---|---|
| GET | `/intelligence/overview` | Pulse, comparison, runway, safe_to_save, story, health |
| GET | `/intelligence/comparison` | Spending comparison (current vs previous period) |
| GET | `/intelligence/story` | Money story — timeline of income/spending events |
| GET | `/intelligence/safe-to-save?days=7` | Safe-to-save calculation |
| GET | `/intelligence/runway` | Money runway — days remaining at current pace |

### Transactions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/transactions` | Paginated list with filters (`category`, `direction`, `q`, `page`, `page_size`) |
| GET | `/transactions/categories` | All category names |
| GET | `/transactions/summary` | Spending summary by category |
| POST | `/transactions/check-impact` | Check if a transaction exceeds safe-to-spend |
| GET | `/transactions/{id}` | Single transaction detail |
| GET | `/transactions/{id}/context` | Category context + comparison |
| PATCH | `/transactions/{id}/category` | Correct category (stored for learning) |

### Send Money (Intent-to-Action Draft)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/transactions/draft` | Create transfer draft |
| GET | `/transactions/draft/active` | Get active draft |
| POST | `/transactions/draft/{id}/review` | Mark draft as reviewed |
| POST | `/transactions/draft/{id}/confirm` | Confirm transfer details |
| POST | `/transactions/draft/{id}/execute` | Execute transfer (**requires PIN**) |
| DELETE | `/transactions/draft/{id}` | Cancel draft |

### Recipients

| Method | Endpoint | Description |
|---|---|---|
| GET | `/recipients/search?q=` | Search contacts |
| GET | `/recipients/resolve?q=` | Resolve with ambiguity detection |
| GET | `/recipients/{id}/relationship` | Classify relationship (trusted/known/new/unusual) |

### Budgets

| Method | Endpoint | Description |
|---|---|---|
| GET | `/budgets/recommendation` | Personalized budget recommendation |
| GET | `/budgets/current` | Current active budget |
| POST | `/budgets` | Create budget |
| PUT | `/budgets/{id}` | Update budget |

### Goals

| Method | Endpoint | Description |
|---|---|---|
| GET | `/goals` | All goals |
| POST | `/goals` | Create goal |
| GET | `/goals/{id}` | Goal detail |
| GET | `/goals/{id}/plan` | Feasibility + recommended contributions |
| PUT | `/goals/{id}` | Update goal |
| POST | `/goals/{id}/alternatives/preview` | Alternative goal plans |
| POST | `/goals/{id}/contributions` | Add contribution |
| POST | `/goals/{id}/pause` | Pause goal |
| POST | `/goals/{id}/resume` | Resume goal |
| DELETE | `/goals/{id}` | Delete goal |

### AI Coach

| Method | Endpoint | Description |
|---|---|---|
| POST | `/coach/chat` | Keyword-routed financial Q&A |
| POST | `/coach/run-out-analysis` | Run-out analysis + explanation |
| GET | `/coach/insights` | Spending + recurring insights |
| POST | `/coach/parse-intent` | Deterministic intent parsing |
| GET | `/coach/safe-to-spend` | Safe-to-spend explanation |
| GET | `/coach/income-adaptive` | Variable-income analysis |

### New Assistant (Conversational Action Orchestration)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/assistant/message` | Main entry point — handles all conversational actions |
| POST | `/assistant/actions/{id}/confirm` | Confirm action |
| POST | `/assistant/actions/{id}/authorize` | Authorize with PIN (1234) |
| DELETE | `/assistant/actions/{id}` | Cancel action |

### Analytics

| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/spending?period=month\|week` | Spending by category |
| GET | `/analytics/cashflow` | Cash flow analysis |
| GET | `/analytics/merchants` | Top merchants |
| GET | `/analytics/recurring` | Recurring transactions |
| GET | `/analytics/comparison` | Period comparison |

### Forecast & Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/forecast/cashflow?days=30` | 7–30 day cash flow forecast |
| GET | `/forecast/upcoming-expenses` | Upcoming recurring expenses |
| GET | `/financial-health` | Health score + dimensions |
| GET | `/financial-health/history` | Historical health scores |

### Reports & Alerts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/reports/weekly` | Weekly spending report |
| GET | `/reports/monthly` | Monthly spending report |
| GET | `/alerts` | All alerts |
| PATCH | `/alerts/{id}/read` | Mark alert as read |

### Learning & Offers

| Method | Endpoint | Description |
|---|---|---|
| GET | `/learning/recommended` | Recommended lessons |
| POST | `/learning/{id}/complete` | Mark lesson complete |
| GET | `/offers/recommended` | Personalized offers |
| PATCH | `/offers/preferences` | Update offer preferences |

### Scenarios

| Method | Endpoint | Description |
|---|---|---|
| POST | `/scenarios/simulate` | Read-only "what if" simulation |

### Trusted Helpers

| Method | Endpoint | Description |
|---|---|---|
| GET | `/trusted-helpers` | All helpers |
| POST | `/trusted-helpers` | Add helper |
| DELETE | `/trusted-helpers/{id}` | Remove helper |
| POST | `/trusted-helper/request` | Accessibility helper request |

### Trusted Contacts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/trusted-contacts` | All contacts |
| POST | `/trusted-contacts` | Add contact |
| DELETE | `/trusted-contacts/{id}` | Remove contact |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check → `{"status": "ok"}` |
| GET | `/system/status` | Mode, data source, Groq availability |

---

## 7. Key Services & Business Logic

### `analytics_service.py` — Deterministic Financial Calculations

**All functions are pure Python — no AI, no guessing.**

| Function | What It Does |
|---|---|
| `spending_summary()` | Category totals, percentages, recurring expenses, unusual expenses, period comparison |
| `health_score()` | 0–100 score: saving behavior (30pts), cash-flow stability (20pts), budget adherence (25pts), liquidity buffer (15pts), recurring management (10pts) |
| `budget_recommendation()` | Based on actual cash flow patterns — not generic 50/30/20 rules |
| `goal_plan()` | Feasibility analysis, recommended weekly/monthly contributions, alternative plans |
| `forecast()` | 7–30 day cash flow forecast with recurring transaction detection |
| `run_out_analysis()` | Week-by-week breakdown, largest category increase, expense change % |
| `spending_comparison()` | Current 30-day window vs previous 30-day window |
| `safe_to_save()` | Conservative weekly savings range |
| `money_runway()` | Days remaining at current spending pace |
| `money_story()` | Timeline of income/spending events (human-readable narrative) |
| `money_pulse()` | One-line financial health signal (e.g., "Spending is up 12% vs last month") |
| `simulate_scenario()` | Read-only projection with before/after timeline |

### `groq_service.py` — Bounded AI Explanation Layer

Groq is **only used to explain pre-calculated numbers**. It never calculates.

```
User asks → Deterministic calc (Python) → Evidence → Groq Explain → Natural language
                                              ↓
                                       If Groq unavailable:
                                       Deterministic fallback text
```

**System prompt enforces:**
- Only use provided structured context
- Never invent transactions, balances, predictions, or guarantees
- No lending approvals or shaming language
- Use Bangladeshi Taka (৳)
- User confirmation required before any action

### `intent_service.py` — Deterministic Intent Parsing

Parses user messages without AI:

| Intent | Example Input |
|---|---|
| `send_money` | "send 500 to Fuad" |
| `check_balance` | "how much money do I have" |
| `safe_to_spend` | "what can I afford to spend" |
| `transaction_history` | "show my recent transactions" |
| `recipient_lookup` | "who is Fuad" |
| `mobile_recharge` | "recharge my phone" |
| `bill_payment` | "pay my electricity bill" |
| `financial_question` | "why am I running low" |
| `guided_send_money` | "help me send money to someone" |
| `spending_analysis` | "where is my money going" |
| `money_runway` | "how long will my money last" |
| `savings_help` | "how can I save more" |

Handles Bangla digits (০–৯), `৳` and `tk` currency symbols, Banglish mixed input.

### `assistant_action_service.py` — Conversational Action Orchestrator

This is the main conversational brain:

```
User message → understand_intent() → handle_message()
                                        ↓
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
              Read Actions        Write Actions      Explanations
         (balance, transactions)  (send_money)     (explain_metric)
                     │                 │                 │
                     ▼                 ▼                 ▼
              prepare_action()   create_draft()   explain_metric()
                                          │
                                          ▼
                                   confirm_action()
                                          │
                                          ▼
                                   authorize_action() ← PIN 1234
```

**Intent routing chain:**
1. Groq as JSON classifier (untrusted output — validated locally)
2. Deterministic `intent_service` keyword fallback
3. `fallback_intent()` for completely unknown inputs

### `transaction_draft_service.py` — Send Money State Machine

```
DRAFT → REVIEWED → CONFIRMED → PIN_VERIFIED → COMPLETED
                                        ↘ CANCELLED (any time)
```

**PIN is never stored in the database.** Only the demo PIN "1234" is accepted. On success, a simulated `Transaction` is created and `Account.balance` is updated.

### `recipient_service.py` — Safe Contact Resolution

```
resolve_recipient(query)
    │
    ├─ Exact match (name or phone) → return contact
    ├─ Multiple partial matches → return AMBIGUOUS list (never guess)
    └─ No match → return NOT_FOUND
```

This prevents wrong transfers due to name ambiguity.

### `relationship_service.py` — Contact Classification

| Class | Criteria |
|---|---|
| **trusted** | 5+ transactions AND `is_trusted=True` |
| **known** | 1–4 transactions |
| **new** | 0 transactions |
| **unusual** | 0 transactions AND amount > ৳5,000 |

### `safe_to_spend_service.py`

```
safe_to_spend = balance
              - upcoming_expenses (next 7 days)
              - recommended_reserve (user-configured)
              - reserved_savings (active goal contributions)
```

### `income_adaptive_service.py`

For freelancers/business owners with variable income:
- Analyzes 4-week income pattern
- Calculates variability index
- Suggests a savings range: if above average income → higher savings; if below → lower savings

---

## 8. Frontend Structure

### `src/App.tsx` — Main Entry

**Login Screen:**
- 3 demo profile buttons (Arif student, Nadia salaried, Samiha freelancer)
- Phone preview mockup UI
- Demo tour (5-step walkthrough overlay)

**AppShell (authenticated):**
- Sidebar navigation (collapsible with tooltips)
- Top bar
- Bottom mobile navigation
- Routes: Home, Pulse, Insights, History, Plan, Goals, Scenarios, Reports, Learn, Offers

### Pages (`src/pages.tsx`)

| Page | Route | Description |
|---|---|---|
| Home | `/` | Balance, income/spending metrics, Money Pulse, Quick Actions, recent transactions |
| PulsePage | `/pulse` | Financial overview, snapshot, primary insight, forecast, spending breakdown |
| InsightsPage | `/insights` | Top insight, change ranking, category comparison, health summary, money story |
| HistoryPage | `/history` | Transaction search/filter, summary tab, AI insights tab, detail sheet |
| PlanPage | `/plan` | Budget recommendation with editable category limits |
| GoalsPage | `/goals` | Savings goals via `SavingsGoalsExperience` component |
| ScenarioPage | `/scenarios` | Scenario Lab with 5 types, before/after chart, alternatives |
| ReportsPage | `/reports` | Financial health via `FinancialHealthExperience` |
| LearnPage | `/learn` | Micro-learning lessons |
| OffersPage | `/offers` | Personalized offers |

### Key Components

| Component | Purpose |
|---|---|
| `coach/CoachPanel.tsx` | Conversational AI interface with Guided Mode, Composer, MessageBlock |
| `coach/PinConfirmationModal.tsx` | 4-digit PIN entry modal (demo PIN: 1234) |
| `coach/CoachComponents.tsx` | Draft cards, transfer review, safe-to-spend breakdown, guided progress |
| `ExplainMetricButton.tsx` | Inline metric explanation trigger with Bangla support |
| `goals/*` | Savings goals UI components |
| `health/*` | Financial health UI components |
| `insights/*` | Insights UI components |

### API Client (`src/api/client.ts`)

- Base URL: `/api/v1` (proxied in dev, Vercel in prod)
- JWT stored in `localStorage` as `upay_token`
- `ApiError` thrown on failure with status code

---

## 9. AI Integration (Groq)

### Configuration

| Variable | Value |
|---|---|
| Endpoint | `https://api.groq.com/openai/v1/chat/completions` |
| Model | `llama-3.3-70b-versatile` (configurable via `GROQ_MODEL`) |
| API Key | Via `GROQ_API_KEY` env variable |
| Timeout | 10 seconds |

### Fallback Chain

```
1. GROQ_API_KEY absent?
   → Use deterministic fallback text (no Groq call)

2. Groq API call made
   ↓
3. Groq error or timeout (10s)?
   → Use deterministic fallback text

4. ai_enabled=False in config?
   → Use fallback_intent() for parsing
   → Use deterministic text for everything else

5. Groq returns response
   → Return AI explanation
```

### What Groq Can and Cannot Do

| Groq CAN | Groq CANNOT |
|---|---|
| Explain a health score | Calculate a health score |
| Explain why spending is up | Invent transaction data |
| Summarize cash flow trends | Predict future balances with certainty |
| Paraphrase budget advice | Approve a loan |
| Translate to Bangla | Access the user's real PIN |

---

## 10. Authentication

### Flow

```
1. User clicks demo profile on login screen
2. POST /auth/login with email
3. Backend returns JWT (HS256, 12-hour expiry)
4. Token stored in localStorage as upay_token
5. All subsequent requests: Authorization: Bearer <token>
6. current_user dependency decodes JWT, fetches User from DB
```

### JWT Contents

```json
{
  "sub": "user_id (UUID)",
  "email": "demo.student@upay.local",
  "exp": "expiry timestamp"
}
```

### Demo PIN

- PIN: `1234` (hardcoded demo value)
- Used only for send-money authorization
- **Never stored in the database**
- Displayed as a hint in the PIN modal
- Real production would use hardware security module / OTP

### Security Notes for Production

- Change `JWT_SECRET_KEY` from default
- Use PostgreSQL instead of SQLite
- Deploy behind HTTPS
- Implement proper password hashing (bcrypt/argon2)
- Use real OTP/PIN verification via SMS/hardware token

---

## 11. Key Workflows

### Workflow 1: Send Money (Intent-to-Action)

```
User: "Send 500 to Fuad"
  │
  ├─► POST /assistant/message
  │     understand_intent() → { intent: "send_money", recipient: "Fuad", amount: 500 }
  │
  ├─► resolve_recipient("Fuad") → Contact found
  │
  ├─► create_draft() → TransactionDraft in DRAFT state
  │
  └─► Return draft summary:
        recipient, amount, fee, total,
        balance_after, runway_impact, safe_to_spend_impact
  │
  ▼ Frontend shows TransactionDraftCard
  │
User clicks "Review transfer"
  │
  ├─► POST /assistant/actions/{id}/confirm
  │     state → REVIEWED → CONFIRMED
  │
  └─► Frontend shows PinConfirmationModal
  │
User enters "1234"
  │
  ├─► POST /assistant/actions/{id}/authorize
  │     verify_pin("1234") → SUCCESS
  │     execute_transfer() → creates Transaction, updates Account.balance
  │
  └─► Frontend shows success message
```

### Workflow 2: Ask the AI Coach

```
User: "Why am I running out of money so fast?"
  │
  ├─► POST /coach/chat
  │     intent_service.parse() → spending_analysis
  │
  ├─► analytics_service.spending_summary() → { category_totals, unusual, recurring }
  │
  ├─► groq_service.explain(evidence, question)
  │     → Groq explains the data in natural language
  │     OR fallback text if Groq unavailable
  │
  └─► Return explanation
  │
  ▼ Frontend renders as financial_insight response type
```

### Workflow 3: Explain a Metric

```
User clicks "?" button on Safe-to-Spend card
  │
  ├─► POST /assistant/message
  │     { explain_metric: "safe_to_spend", value: 3500 }
  │
  ├─► explain_metric("safe_to_spend", 3500, language="en")
  │     → Formats breakdown:
  │       Balance: ৳10,500
  │       - Upcoming expenses: ৳3,000
  │       - Recommended reserve: ৳2,000
  │       - Reserved savings: ৳2,000
  │       = Safe to spend: ৳3,500
  │
  └─► Frontend displays breakdown with Bangla if requested
```

### Workflow 4: Savings Goal Planning

```
User: "I want to save ৳50,000 for a laptop in 6 months"
  │
  ├─► POST /goals → Create goal (target: 50000, months: 6)
  │
  ├─► GET /goals/{id}/plan
  │     analytics_service.goal_plan()
  │     → Monthly needed: ৳8,333
  │     → Feasible: YES (current savings rate: ৳12,000/mo)
  │     → Alternative: ৳7,500/mo for 7 months
  │
  └─► Frontend shows plan with feasibility, contribution schedule
  │
User clicks "Start saving"
  │
  ├─► POST /goals/{id}/contributions { amount: 5000 }
  │
  └─► Goal.current_amount += 5000, progress updated
```

---

## 12. Configuration

### Environment Variables

| Variable | Default | Required | Notes |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///./upay_demo.sqlite3` | No | Use PostgreSQL for production |
| `GROQ_API_KEY` | _(empty)_ | No | Optional; fallback works without it |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | No | Any Groq-compatible model |
| `AI_ENABLED` | `True` | No | Set `False` to disable all AI features |
| `JWT_SECRET_KEY` | `demo-only-change-me` | **Yes** | **Must change in production** |
| `FRONTEND_URL` | `http://localhost:5173` | No | CORS allowed origins |
| `ENVIRONMENT` | `development` | No | `development` or `production` |

### `.env.example`

```bash
cp backend/.env.example backend/.env
# Then edit backend/.env and add your GROQ_API_KEY
```

---

## 13. Important Constraints

| ⚠️ | Constraint |
|---|---|
| **Synthetic data only** | No real upay API, no real money, no real financial connections |
| **PIN is demo only** | "1234" is hardcoded; never use in production |
| **JWT_SECRET_KEY** | Must be changed from default before any production deployment |
| **Never commit `.env`** | It's in `.gitignore` — secrets stay local |
| **Groq is optional** | The full app works without it via deterministic fallbacks |
| **Bangladeshi Taka only** | All amounts are in ৳ (BDT); no other currencies |
| **No real payments** | All transfers are simulated within the demo database |

---

## 14. Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # Add GROQ_API_KEY (optional)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# API available at http://localhost:8000/api/v1
```

### Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

### Demo Login

Visit `http://localhost:5173`, then click any demo profile:
- **Arif** (student) — `demo.student@upay.local` / `password`
- **Nadia** (salaried) — `demo.salary@upay.local` / `password`
- **Samiha** (freelancer) — `demo.freelancer@upay.local` / `password`
- **Rafi** (business) — `demo.business@upay.local` / `password`

### Deploy to Vercel

The frontend deploys automatically via Vercel Git integration. For manual deploy:

```bash
cd frontend
npm run build
vercel --prod
```

Backend runs on Vercel Functions (Python runtime) automatically from the `backend/` directory.

---

*Last updated: October 2026 — for the AI DEV FEST 2026 hackathon demo*
