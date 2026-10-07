# Upay AI Financial Coach — Project Documentation

> **Prototype for DIU CPC × upay AI Hackathon / AI DEV FEST 2026**
> All data is synthetic. This is NOT an official upay service.

---

## Table of Contents

1. [What This Project Is](#what-this-project-is)
2. [The Core Philosophy](#the-core-philosophy)
3. [Why the Architecture Is Built This Way](#why-the-architecture-is-built-this-way)
4. [Frontend (React/TypeScript)](#frontend-reacttypescript)
5. [Backend (FastAPI/Python)](#backend-fastapipython)
6. [Database Layer (SQLAlchemy 2)](#database-layer-sqlalchemy-2)
7. [AI Integration (Groq + Deterministic Fallback)](#ai-integration-groq--deterministic-fallback)
8. [Financial Calculations (Deterministic Services)](#financial-calculations-deterministic-services)
9. [Intent-to-Action Workflow](#intent-to-action-workflow)
10. [ML Models (Random Forest)](#ml-models-random-forest)
11. [People Features](#people-features)
12. [Helper Mode (Trusted Family Access)](#helper-mode-trusted-family-access)
13. [Security Design](#security-design)
14. [API Reference Summary](#api-reference-summary)
15. [Design Decisions Explained](#design-decisions-explained)
16. [Future Production Path](#future-production-path)

---

## What This Project Is

**Upay AI Financial Coach** is an AI-powered financial guidance layer for Mobile Financial Services (MFS) users — specifically built for the Bangladesh market. It wraps around a user's transaction history and provides:

- Conversational financial coaching in English, Bangla, or mixed code-switched text
- Deterministic calculations for balances, budgets, savings goals, and forecasts
- An **Intent-to-Action** workflow that guides users through money transfers with AI explanation at every step
- **Trusted Helper Mode** so family members can assist without sharing credentials
- A personal **Financial Health Score** (0–100) that is explainable and not a credit score
- **Spending forecasts** using a Random Forest ML model trained on the user's own transaction patterns

The project uses **synthetic demo data only**. No real upay API is called, no real money moves.

---

## The Core Philosophy

### Evidence-First AI

> **AI explains what the numbers mean. Deterministic code calculates what the numbers are.**

This is the single most important architectural principle:

```
┌─────────────────────────────────────────────────────┐
│  TRANSACTION DATA                                   │
│  (stored, synthetic)                               │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  DETERMINISTIC ANALYTICS                           │
│  safe_to_spend, money_pulse, health_score,         │
│  forecast, spending_summary, money_runway...         │
│  Always returns the same result for the same data.  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  EVIDENCE OBJECT (JSON)                            │
│  { category: "Food", total: 4500, percent: 32% } │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  AI (Groq or Fallback)                             │
│  "Food is your largest spending category at 32%     │
│   of total expenses. This is ৳500 more than last   │
│   month..."                                       │
└─────────────────────────────────────────────────────┘
```

**Why this separation?**

- Deterministic calculations are auditable, testable, and legally defensible. If the AI says "you spent ৳500 on food," that number must be provably correct.
- Separating calculation from explanation means the AI can never influence a balance, a score, or a transfer amount.
- Fallback responses (when Groq is unavailable) still work because the evidence is pre-computed.

### Financial Safety Boundary

```
AI's domain:                          AI's domain NEVER includes:
────────────────────────               ──────────────────────────────────
• Natural language explanations         • Actual balance calculations
• Spending category narratives         • Budget limit computations
• Coaching and tips                   • Safe-to-spend thresholds
• Goal progress interpretations        • Forecast numerical outputs
• Conversation in Bangla/English       • PIN verification
                                       • Transaction execution
```

### Intent-to-Action State Machine

Every money movement follows this strict state machine:

```
DRAFT ──► REVIEWED ──► CONFIRMED ──► PIN_VERIFIED ──► COMPLETED
  │          │            │              │                │
  │          │            │              │                │
 User      AI +       User           App-side        Transfer
 creates   User        confirms        PIN only         happens
 draft     review      intent         (AI never        HERE
 details                  │            sees it)
                           │
                           ▼
                     User enters
                     PIN in app
                     (AI blind)
```

**Why states?**

- Each transition requires explicit user consent
- The AI explains each step before it happens
- PIN is application-side only — verified against a stored hash, never sent to AI, never logged
- At any point, the user can cancel and the draft is discarded

---

## Why the Architecture Is Built This Way

### React + Vite + TypeScript (Frontend)

| Decision | Reason |
|----------|--------|
| **React 18** | Component-based, mature ecosystem, strong TypeScript support |
| **Vite** | Fast HMR for rapid development; fast builds for production |
| **TypeScript** | Catches API contract mismatches at compile time; essential for a financial app |
| **Tailwind CSS** | Utility-first; consistent design without a large component library dependency |
| **Recharts** | Lightweight, composable charts for spending breakdowns |
| **Lucide React** | Clean, MIT-licensed icon set |
| **React Router** | Client-side routing without full-page reloads |
| **Context API** | Simple auth and coach-panel state without Redux overhead |

### FastAPI + SQLAlchemy 2 (Backend)

| Decision | Reason |
|----------|--------|
| **FastAPI** | Async, automatic OpenAPI docs, Pydantic validation, ideal for an API-first backend |
| **SQLAlchemy 2** | Full ORM with async support; `Mapped []` typed column definitions |
| **Pydantic v2** | Request/response validation, `BaseModel.dict()` method |
| **Python** | Ecosystem for ML (scikit-learn), financial calculations, and AI integration |
| **SQLite (dev)** | Zero-config, file-based, `DEMO_DATA=1` for synthetic seed |
| **PostgreSQL (prod)** | Production-grade relational data; Railway/Render compatible |

### JWT Authentication

- **HMAC-SHA256** signed tokens (not RS256 which requires key pairs)
- Token contains only `user_id`; all other data fetched from DB
- Token is decoded on every authenticated request via `Depends(current_user)`
- `JWT_SECRET_KEY` must be changed from `demo-only-change-me` in production

---

## Frontend (React/TypeScript)

### Key Files

| File | Role |
|------|------|
| `src/App.tsx` | Root component; routing, auth context, coach panel layout |
| `src/client.ts` | API client with `fetch` wrapper; attaches JWT to every request |
| `src/pages.tsx` | Route definitions and lazy-loaded page components |
| `src/components/CoachPanel.tsx` | Persistent AI coach panel; chat, explain-metric, confirm flows |

### App Structure

```
App
├── AuthContext (JWT storage, login state)
├── Router
│   ├── / (redirect → /dashboard or /login)
│   ├── /login
│   ├── /dashboard        ← main financial overview
│   ├── /transactions     ← transaction list with filters
│   ├── /budgets         ← budget creation and plan acceptance
│   ├── /goals           ← savings goals with contribution tracking
│   ├── /coach           ← full-screen coach chat
│   ├── /reports         ← weekly/monthly reports
│   ├── /learning        ← financial literacy lessons
│   ├── /offers          ← personalized cashback offers
│   ├── /people          ← trusted contacts for Send Money
│   └── /settings        ← language, preferences
└── CoachPanel (always visible on desktop)
    ├── Chat messages
    ├── Explain-metric popups
    └── Confirm/cancel action buttons
```

### API Client (`client.ts`)

```typescript
// Every request:
// 1. Attaches Authorization: Bearer <token>
// 2. Parses error responses into { error: string }
// 3. unwraps { data: T } envelopes
// 4. Throws on non-2xx status
```

### Demo Personas (Synthetic Users)

| Email | Persona | Balance | Profile |
|-------|---------|---------|---------|
| `demo.student@upay.local` | Student | ৳3,200 | Low income, high food spending |
| `demo.salary@upay.local` | Salaried | ৳18,500 | Regular income, rent + transport |
| `demo.freelancer@upay.local` | Freelancer | ৳7,800 | Irregular income, variable spending |

All passwords: `password`

---

## Backend (FastAPI/Python)

### Request Flow

```
HTTP Request
    │
    ▼
FastAPI Route (@app.post, @app.get, ...)
    │
    ▼
Pydantic In schema (Body, Query, Path params)
    │
    ▼
Depends(current_user) → JWT decode → DB User lookup
    │
    ▼
Service Layer (analytics_service, groq_service, ...)
    │
    ▼
DB writes via SQLAlchemy Session
    │
    ▼
Pydantic Out schema → JSON Response
```

### Key Services

#### `analytics_service.py` — Deterministic Financial Calculations

All functions here take `db, user` and return pure JSON-serializable dicts. No AI, no randomness (except `random` for demo transaction generation in `seed.py`).

| Function | Returns | Formula |
|----------|---------|---------|
| `spending_summary()` | Category totals, biggest category, frequent merchants | `SUM(amount) GROUP BY category` |
| `health_score()` | 0–100 score + explainable factors | Savings rate (40%) + budget adherence (30%) + balance buffer (30%) |
| `budget_recommendation()` | 50/30/20 rule adapted for Bangladesh | Essential (rent, food, transport) vs flexible vs savings |
| `goal_plan()` | Monthly contribution needed to reach goal | `(target - current) / months_remaining` |
| `forecast()` | Predicted expenses for N days | Average daily spending × days + recurring expenses |
| `run_out_analysis()` | Which categories caused overspend | Daily spending vs available balance |
| `money_pulse()` | Income vs spending balance signal | Income − Spending for period |
| `money_runway()` | Days until balance hits zero at current rate | `balance / avg_daily_spend` |
| `safe_to_save()` | How much can realistically be saved | `income - essential_spend - safety_buffer` |
| `money_story()` | Month-over-month narrative | Comparison text + percentage change |
| `spending_comparison()` | This month vs last month per category | `current_category / previous_category − 1` |
| `simulate_scenario()` | What-if projections (no DB write) | Deterministic budget arithmetic |

#### `groq_service.py` — AI Explanations

```python
async def explain(topic: str, evidence: dict, question: str, language: str) -> str:
    # topic: "run_out" | "chat" | "safe_to_save" | "budget_review" | "forecast"
    # evidence: pre-computed deterministic results
    # Falls back to template strings if GROQ_API_KEY absent or request fails
```

Model: `qwen/qwen3.8-27b` (free tier compatible, handles code-switched Bangla-English).

**Fallback behavior**: If Groq is unavailable (no API key, rate limit, network error), returns a deterministic template response using the `evidence` dict directly. The UI never shows an error — it just shows the calculated numbers with a short label.

#### `assistant_action_service.py` — Conversational AI Orchestrator

Handles the `/assistant/message` endpoint. This is the **single entry point** for all coach conversations.

- `handle_message()` — parses free-form text, routes to appropriate evidence, calls Groq
- `explain_metric()` — triggers a structured explanation of a specific metric (health score, safe-to-spend, etc.)
- `confirm_action()` / `authorize_action()` / `cancel_action()` — state machine transitions for Intent-to-Action

#### `safe_to_spend_service.py` — Safe-to-Spend Engine

```python
calculate_safe_to_spend(db, user) → {
    "can_spend": 1200,
    "reserved_bills": 800,
    "committed_transfers": 200,
    "available_after_commitments": 1000,
    "breakdown": {...}
}
```

Factors in: upcoming recurring bills, active budget utilization, pending Send Money drafts, savings goal contributions, safety buffer.

#### `transaction_draft_service.py` — Intent-to-Action Draft Management

Manages the `TransactionDraft` model and the state machine:

```python
DraftState:
    "draft_created"  → initial
    "reviewed"       → user confirmed details
    "confirmed"      → user confirmed intent
    "pin_verified"   → app-side PIN check passed
    "executed"       → transfer completed (demo only)
    "cancelled"      → user abandoned
```

Key functions:
- `create_draft()` — creates a draft from AI-parsed intent
- `review_draft()` — transitions DRAFT → REVIEWED
- `confirm_draft()` — transitions REVIEWED → CONFIRMED
- `verify_pin()` — checks PIN hash, transitions CONFIRMED → PIN_VERIFIED
- `execute_draft()` — in demo mode, just updates balance (no real transfer)

#### `recipient_service.py` — Trusted Contacts

- `add_trusted_contact()` — saves a person with phone + relationship
- `find_best_contact_match()` — fuzzy search on name/phone/relationship
- `resolve_recipient()` — server-side disambiguation; **never guesses**, returns ambiguity list
- Phone numbers normalized to `8801XXXXXXXXX` format for consistency

#### `relationship_service.py` — Transaction History Analysis

Classifies the user's relationship to a recipient based on transaction history:

```python
classify_relationship(db, user, contact, recipient_name, amount) → {
    "relationship_type": "frequent_family" | "occasional_merchant" | "first_time" | ...,
    "previous_transaction_count": 12,
    "last_transaction_amount": 500.0,
    "average_transaction_amount": 450.0,
    "total_sent": 5400.0,
    "evidence": {...}
}
```

Used by the AI to contextualize Send Money requests: "You're sending ৳500 to your mother for the 5th time this month."

#### `helper_mode_service.py` — Trusted Helper Mode

Family member (helper) can be granted granular permissions:

| Permission | What it allows |
|------------|----------------|
| `view_financial_health` | See health score + spending breakdown |
| `view_pending_transaction` | See drafts awaiting confirmation |
| `prepare_transaction` | Fill in transaction details for owner to review |
| `receive_alerts` | Get notified of low balance |

**Key design**: Helpers never see the PIN. Owners can revoke access instantly. All activity is audited in `HelperActivity`.

#### `ml_financial_service.py` — Random Forest Forecasting

Trains a `RandomForestRegressor` on the user's own transaction history:

```python
features = [
    day_of_week,        # 0–6
    week_of_month,       # 1–5
    day_of_month,        # 1–31
    is_payday,          # 0/1 (detected from income transactions)
    category_encoded,    # per-category models
    recurring_score,      # 0.0–1.0 (how consistent this category is)
]

target = daily_spending_amount
```

Trained on last 90 days of data, refitted on every `/transactions` write.

**Why Random Forest?**

- Handles non-linear relationships (spending spikes on paydays)
- Works with small datasets (90 days × ~10 transactions/day = 900 samples)
- Interpretable feature importances for explaining predictions
- `sklearn` is pure Python, no GPU required

### ML Model Service (`ml/model_service.py`)

```python
get_model_service().load()
# Loads pre-trained artifact if it exists
# Falls back to zero-trained model gracefully
# Never crashes the app if the artifact is corrupt
```

---

## Database Layer (SQLAlchemy 2)

### Key Models

```
users
├── accounts (1:1) — balance, currency
├── transactions (1:N) — every income/spending/transfer
├── budgets (1:N) — active + replaced history
├── plan_states (1:1) — user's saved 50/30/20 plan
├── savings_goals (1:N) — each with goal_plan_settings
├── trusted_contacts (1:N) — people for Send Money
├── helper_relationships (1:N) — trusted helpers
├── assistant_conversations (1:N) — chat threads
│   └── assistant_action_drafts (1:N) — state machine drafts
├── financial_lessons (static) + lesson_progress (per-user)
├── offers (static) + saved_offers (per-user)
├── notifications (1:N)
└── financial_insights (1:N) + health_snapshots (1:N)
```

### Decimal Handling

All monetary amounts stored as `Numeric(14, 2)` in the DB. In Python, the `Decimal` type is used throughout services. The schema exposes amounts as floats via `amount()` helper (which calls `float()` for JSON serialization).

```python
# Pydantic models use float
# DB layer uses Decimal
# analytics_service uses Decimal throughout
# Output uses float(x) via amount()
```

---

## AI Integration (Groq + Deterministic Fallback)

### How a Coach Chat Works

```
1. User types: "Why did I run out of money this month?"
2. /coach/chat receives question
3. Deterministic: run_out_analysis() → { category_spends, overspend_days, ... }
4. Groq called with:
   - system: "You are a financial coach. Explain in {language}."
   - user: "{question}\n\nEvidence: {evidence_json}"
5. If Groq succeeds → return explanation
   If Groq fails → return template fallback: "Your spending was highest
   in {biggest_category} at ৳{total}. Review {suggestion}"
```

### Why Groq?

- Free tier available (qwen/qwen3.8-27b)
- Handles code-switched Bangla-English prompts well
- Server-side only — API key never exposed to frontend
- Low latency compared to OpenAI for this use case

### Bangla Support

Many Bangladesh users code-switch between Bangla and English. The coach detects the language from:

1. `preferred_language` stored in user profile
2. Per-message `language` field in `/coach/chat`
3. Per-conversation `language` in assistant state

Content in `financial_lessons` has `content_bn` fields for full Bangla versions.

---

## Financial Calculations (Deterministic Services)

### Financial Health Score

```
score = (savings_rate_component × 0.4) + (budget_adherence × 0.3) + (balance_buffer × 0.3)

savings_rate_component:
  if monthly_income > 0: min(savings / income * 100, 100)
  else: 0

budget_adherence:
  100 if no_budget
  else: max(0, 100 - (overspend_percentage))

balance_buffer:
  min(balance / avg_monthly_expense * 20, 100)  capped at 20% of monthly expense = 100
```

Score is 0–100. It is **NOT** a credit score — it never leaves the private app, never impacts eligibility.

### Money Runway

```python
runway_days = current_balance / avg_daily_spending
# avg_daily_spending = total_spending_30d / 30
# If avg_daily_spending == 0: runway_days = float('inf')
```

### Safe-to-Spend

```python
safe_to_spend = (
    current_balance
    - reserved_for_bills          # upcoming recurring
    - active_budget_limit       # budget.utilization
    - pending_draft_amounts      # unreviewed Send Money drafts
    - savings_goal_contributions # this month's planned contributions
    - safety_buffer             # 10% of balance (configurable)
)
```

---

## Intent-to-Action Workflow

### Full Send Money Flow

```
1. User tells Coach: "Send 500 to Ma tomorrow rent"
   → /coach/parse-intent extracts { amount: 500, recipient: "Ma", ... }

2. User confirms: "Yes that's right"
   → /assistant/message returns action draft with review step

3. User clicks "Review" on draft
   → POST /transactions/draft/{id}/review
   → State: DRAFT → REVIEWED

4. Coach explains: "You're sending ৳500 to Mother.
   Your safe-to-spend is ৳1,200.
   After this transfer you'll have ৳700 left."
   → User reads, understands

5. User clicks "Confirm"
   → POST /transactions/draft/{id}/confirm
   → State: REVIEWED → CONFIRMED
   → Response: { requires_pin: true }

6. User enters PIN in the app (NOT in chat)
   → PIN verified against stored hash (app-side only)
   → State: CONFIRMED → PIN_VERIFIED

7. App executes transfer (demo: balance update)
   → POST /transactions/draft/{id}/execute
   → State: PIN_VERIFIED → EXECUTED
```

**Critical: PIN never enters chat, never goes to AI, never logged in plain text.**

### Explain-Metric Flow

```
User clicks on "Health Score: 72"
→ /assistant/message with { explain_metric: "health_score" }
→ analytics_service.health_score() → { score: 72, factors: {...} }
→ Groq explains: "Your score of 72 is good because you saved
  18% of income this month (target: 20%)..."
```

---

## ML Models (Random Forest)

### Training Data

```python
# Features per transaction:
day_of_week, week_of_month, is_payday, days_since_payday,
category_encoded, amount, is_recurring, merchant_frequency_score

# For forecasting: predict next 14 days daily spending
# Model: RandomForestRegressor(n_estimators=100, max_depth=5)
```

### Feature Importances

The model learns which features matter most for each user's spending:

1. **day_of_week** — weekend vs weekday patterns
2. **is_payday** — income arrival changes spending capacity
3. **category** — some categories are more predictable than others
4. **recurring_score** — subscriptions vs one-time purchases

### Risk Classification

```python
get_financial_risk(db, user) → {
    "risk_level": "low" | "medium" | "high",
    "factors": ["low_buffer_days", "overspend_trend"],
    "runway_days": 12,
    "suggestions": [...]
}
```

Uses a rule-based overlay on top of the ML forecast:
- `high` if runway < 7 days OR health_score < 30
- `medium` if runway < 14 days OR health_score < 50
- `low` otherwise

---

## People Features

### Trusted Contacts

Users save people (family, friends, landlords) with:
- Name, phone number (normalized to E.164-ish format)
- Relationship label ("Mother", "Landlord", "Friend")
- Optional nickname and notes
- Verification status (unverified → needs_review → verified)

**Verification workflow**: When a user sends money to a saved contact, the app checks if the phone number matches. If not, the contact is flagged for review.

### Recipient Search

```
GET /recipients/search?q="Mum"
→ fuzzy match on name, phone, relationship
→ returns top 5 matches with is_trusted flag

GET /recipients/resolve?q="Baba"
→ if single match → status: "resolved", contact: {...}
→ if multiple → status: "ambiguous", matches: [...]
→ if none → status: "not_found"
```

Server **never guesses** — ambiguity is always returned as ambiguity.

---

## Helper Mode (Trusted Family Access)

### Permission Model

Each helper relationship has a JSON list of permissions:
```json
["view_financial_health", "view_pending_transaction", "prepare_transaction"]
```

### How It Works

1. **Owner** creates a helper relationship (name, phone, relationship)
2. **Helper** receives an invitation (in production: SMS or QR code scan)
3. **Helper** accepts → relationship becomes `active`
4. Helper can now see restricted views based on their permissions

### Activity Audit

Every action by a helper is logged in `HelperActivity`:
```json
{ "actor": "helper", "event_type": "helper_viewed_financial_health", "detail": "..." }
```

### Assistance Requests

A helper with `prepare_transaction` permission can prepare a transaction for the owner to review:
- Helper fills in amount, recipient, reference
- Owner sees it as a pending request
- Owner confirms → enters their own PIN → transfer executes

**The helper can never authorize a transfer. Only prepare details.**

---

## Security Design

### Authentication

```
POST /auth/login { email, password }
→ bcrypt check against stored hash
→ returns JWT (HMAC-SHA256, 24h expiry)
→ Frontend stores in localStorage, attaches to every request
```

### PIN Storage

- PIN is hashed with bcrypt
- Stored in the `accounts` table (or separate `user_pins` table in production)
- Verified in `verify_pin()` — never sent to AI, never in logs
- Max 3 attempts before draft is cancelled

### CORS

```python
allow_origins=[get_settings().frontend_url]  # e.g., http://localhost:5173
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
allow_headers=["Authorization", "Content-Type"]
```

### Production JWT

In `production`/`staging` environment:
```python
if settings.jwt_secret_key == "demo-only-change-me":
    raise RuntimeError("JWT_SECRET_KEY must be configured")
```

---

## API Reference Summary

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password, returns JWT |
| GET | `/api/v1/auth/me` | Current user profile |

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard/summary` | Full dashboard: balance, spending, health, forecast, AI insight |

### AI Coach

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/assistant/message` | Free-form chat + structured explain-metric |
| POST | `/api/v1/assistant/actions/{id}/confirm` | Confirm action draft |
| POST | `/api/v1/assistant/actions/{id}/authorize` | Authorize with PIN |
| DELETE | `/api/v1/assistant/actions/{id}` | Cancel action |
| POST | `/api/v1/coach/chat` | Simple chat with intent detection |
| POST | `/api/v1/coach/parse-intent` | Parse natural language into structured intent |
| GET | `/api/v1/coach/safe-to-spend` | Safe-to-spend calculation |
| GET | `/api/v1/coach/income-adaptive` | Income-adaptive budget |

### Financial Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/intelligence/overview` | Pulse, runway, comparison, story |
| GET | `/api/v1/intelligence/safe-to-save` | Safe-to-save for N days |
| GET | `/api/v1/intelligence/runway` | Money runway |
| GET | `/api/v1/intelligence/story` | Month narrative |
| POST | `/api/v1/scenarios/simulate` | What-if projection (read-only) |

### Transactions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/transactions` | Paginated list with filters |
| GET | `/api/v1/transactions/{id}` | Single transaction |
| GET | `/api/v1/transactions/{id}/context` | Category + comparison context |
| PATCH | `/api/v1/transactions/{id}/category` | Correct category |
| POST | `/api/v1/transactions/check-impact` | Impact of hypothetical spend |
| POST | `/api/v1/transactions/draft` | Create Send Money draft |
| GET | `/api/v1/transactions/draft/active` | Current draft state |
| POST | `/api/v1/transactions/draft/{id}/review` | DRAFT → REVIEWED |
| POST | `/api/v1/transactions/draft/{id}/confirm` | REVIEWED → CONFIRMED |
| POST | `/api/v1/transactions/draft/{id}/execute` | PIN verify + execute |
| DELETE | `/api/v1/transactions/draft/{id}` | Cancel draft |

### Budgets & Plans

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/budgets/plan` | Current plan + recommendation |
| PUT | `/api/v1/budgets/plan` | Save custom plan |
| POST | `/api/v1/budgets/plan/accept` | Accept plan → creates active budget |
| GET | `/api/v1/budgets/current` | Active budget with utilization |
| POST | `/api/v1/budgets` | Create budget |
| PUT | `/api/v1/budgets/{id}` | Update budget |
| GET | `/api/v1/budgets/recommendation` | AI-generated budget recommendation |

### Savings Goals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/goals` | All goals with plan |
| POST | `/api/v1/goals` | Create goal |
| GET | `/api/v1/goals/{id}` | Goal detail + plan |
| PUT | `/api/v1/goals/{id}` | Update goal |
| POST | `/api/v1/goals/{id}/contributions` | Add money to goal |
| POST | `/api/v1/goals/{id}/pause` | Pause goal |
| POST | `/api/v1/goals/{id}/resume` | Resume goal |
| DELETE | `/api/v1/goals/{id}` | Delete goal |
| POST | `/api/v1/goals/{id}/alternatives/preview` | What-if goal changes |

### People (Trusted Contacts)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/trusted-people` | List trusted contacts |
| POST | `/api/v1/trusted-people` | Add contact |
| GET | `/api/v1/trusted-people/{id}` | Contact detail + activity |
| PUT | `/api/v1/trusted-people/{id}` | Update contact |
| POST | `/api/v1/trusted-people/{id}/verify` | Verify phone number |
| DELETE | `/api/v1/trusted-people/{id}` | Remove contact |
| GET | `/api/v1/recipients/search` | Search recipients |
| GET | `/api/v1/recipients/resolve` | Resolve ambiguous query |

### Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reports/weekly` | Weekly spending report |
| GET | `/api/v1/reports/monthly` | Monthly spending report |

### Learning

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/learning/recommendations` | Personalized lesson recommendations |
| GET | `/api/v1/learning/lessons` | All lessons |
| GET | `/api/v1/learning/lessons/{id}` | Lesson detail + quiz |
| POST | `/api/v1/learning/{id}/start` | Mark lesson started |
| POST | `/api/v1/learning/{id}/complete` | Mark lesson completed |
| GET | `/api/v1/learning/progress` | Category progress summary |

### Offers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/offers` | Personalized offers |
| GET | `/api/v1/offers/saved` | Saved offers |
| POST | `/api/v1/offers/{id}/save` | Save offer |
| DELETE | `/api/v1/offers/{id}/save` | Unsave offer |
| PUT | `/api/v1/offers/preferences` | Toggle personalization |

### Trusted Helper Mode

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/trusted-helpers` | List helpers |
| POST | `/api/v1/trusted-helpers` | Create helper relationship |
| GET | `/api/v1/trusted-helpers/{id}` | Helper detail + permissions |
| PUT | `/api/v1/trusted-helpers/{id}/permissions` | Update permissions |
| POST | `/api/v1/trusted-helpers/{id}/revoke` | Revoke access |
| GET | `/api/v1/trusted-helpers/{id}/activity` | Helper activity log |
| GET | `/api/v1/helper-requests` | Pending assistance requests |
| POST | `/api/v1/helper-requests/{id}/review` | Accept/reject request |
| GET | `/api/v1/helper-invitations` | My invitations to help others |

### ML

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/ml/forecast` | 14-day spending forecast |
| GET | `/api/v1/ml/risk` | Financial risk classification |
| GET | `/api/v1/ml/summary` | ML overview for dashboard |
| GET | `/api/v1/ml/metrics` | Model training metrics |

---

## Design Decisions Explained

### Why 50/30/20 for Bangladesh?

The classic 50/30/20 rule (needs/wants/savings) was adapted because:

- Bangladesh MFS users often have **high essential spend** (rent, food, transport) relative to income
- A student's essential spend can be 70%+ of income
- The recommendation engine **adapts to income level** — lower income users get a lower essential target
- "Flexible" includes discretionary categories (shopping, entertainment)

### Why Random Forest for Forecasting?

Linear models (ARIMA, linear regression) fail on:
- **Payday spikes** — a 3-day average doesn't capture sudden large inflows/outflows
- **Category interactions** — food spending is higher on weekends, transport higher on weekdays
- **Recurring variance** — subscriptions vary in amount and date

Random Forest handles these non-linearities without:
- Feature engineering time series (which needs more data)
- Deep learning (which needs GPU and more samples)
- Per-user model retraining (the forest is per-user by design)

### Why PIN verification in the app layer?

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  User    │───▶│  App     │───▶│  Backend │
│  enters  │    │  hashes  │    │  verifies │
│  PIN     │    │  PIN     │    │  hash     │
└──────────┘    └──────────┘    └──────────┘
```

- The PIN **hash** is stored server-side (bcrypt)
- The PIN **value** never leaves the device
- The AI **never sees it** — even if the AI prompt is injected, there's nothing to extract
- This is a **defense in depth** measure, not security theater

### Why Trusted Helper Mode uses a separate relationship?

A helper is **not a user** — they don't have an account, balance, or transactions. They're a "lite" access grant attached to the owner's account. This avoids:
- Creating fake accounts for family members
- Requiring helpers to go through KYC
- Mixing helper activity with real user activity

### Why SQLite for development?

- **Zero configuration** — `pip install -r requirements.txt && uvicorn app.main` just works
- **File-based** — the `.db` file can be checked into a demo branch
- **SQLite dialect in SQLAlchemy** works identically to PostgreSQL for all queries used
- Production just changes `DATABASE_URL=postgresql://...`

---

## Future Production Path

| Step | Action | Why |
|------|-------|-----|
| 1 | Change `JWT_SECRET_KEY` to a 256-bit random hex | Prevent token forgery |
| 2 | Provision PostgreSQL (Railway, Render, Supabase) | Production-grade ACID compliance |
| 3 | Add KYC verification to user registration | Legal requirement for MFS |
| 4 | Replace synthetic transactions with real upay API | Real balances and transactions |
| 5 | Integrate BKash/Nagad/Upay Send Money API | Actual money movement |
| 6 | Add transaction signing with hardware HSM | Legal audit trail |
| 7 | Deploy to Vercel (frontend) + Railway (backend) | Edge CDN + managed DB |
| 8 | Add rate limiting and IP allowlisting | Abuse prevention |
| 9 | Implement OWASP Top 10 mitigations | Security hardening |
| 10 | Add consent logging for AI explanations | Regulatory compliance |

---

*This document was created for the DIU CPC × upay AI Hackathon / AI DEV FEST 2026. All features described are implemented in the current codebase unless marked as "planned."*
