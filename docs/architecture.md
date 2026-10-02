# Architecture

```mermaid
flowchart LR
  UI[React + Vite + Tailwind-style CSS] --> API[FastAPI /api/v1]
  API --> DB[(PostgreSQL via SQLAlchemy)]
  API --> Calc[Deterministic analytics]
  Calc --> Forecast[Interpretable forecast & pattern rules]
  Calc --> Context[Structured financial context]
  Context --> Groq[Groq explanation]
  Groq --> Validate[Fallback / safety boundary]
  Validate --> UI
  Seed[SyntheticTransactionProvider] --> DB
```

`SyntheticTransactionProvider` is presently implemented by the seed service. A future `UpayTransactionProvider` would sit behind the same data-ingestion boundary only after consent, governance, API access, anonymization, and security review. No production upay API is claimed.

The app defaults to SQLite only for easy local demo startup; `DATABASE_URL` supports PostgreSQL/psycopg and Docker Compose provides Postgres. Production uses PostgreSQL, migrations, restricted CORS, a non-default JWT secret, and TLS at the deployment edge.
