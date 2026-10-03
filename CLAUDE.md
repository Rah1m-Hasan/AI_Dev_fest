# CLAUDE.md — Upay AI Financial Coach

## Project Overview

**Upay AI Financial Coach** is a hackathon concept prototype for DIU CPC × upay AI Hackathon / AI DEV FEST 2026. It uses synthetic demo data only and is NOT an official production upay service.

## Quick Start Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Add your GROQ_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

**Demo login:** `demo.student@upay.local` / `password`

## Key Constraints

- **Synthetic data only** — no real upay API, no real money
- **JWT_SECRET_KEY** must be changed in production
- **GROQ_API_KEY** is optional — falls back to deterministic responses if absent
- **Never commit `.env`** — it's in `.gitignore`

## Architecture

```
Frontend (React/Vite) → Backend (FastAPI) → SQLite/PostgreSQL
                      → Deterministic Analytics
                      → Groq (optional, server-side only)
```

## Important Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, all API routes |
| `backend/app/services/groq_service.py` | Groq integration with fallback |
| `backend/app/services/analytics_service.py` | Deterministic financial calculations |
| `backend/app/services/seed.py` | Synthetic demo data generator |
| `frontend/src/App.tsx` | Main React app |
| `docs/` | Architecture, privacy, AI design docs |

## Groq Configuration

- Model: `qwen/qwen3.8-27b` (free tier compatible)
- Key is read from `backend/.env` (not project root)
- If Groq fails, falls back to deterministic text responses

## API Base URL

- Backend: `http://localhost:8000/api/v1`
- Frontend proxies `/api` to backend in development
