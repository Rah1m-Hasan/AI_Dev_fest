# Privacy, security and responsible AI

This prototype uses synthetic data only. It stores a minimal demo identity, account balance and transaction records needed to demonstrate the product. It does not collect protected attributes, authenticate to upay, make lending decisions, transfer money, restrict accounts, or promise outcomes.

Secrets are environment variables only. API inputs are Pydantic-validated, ORM queries are parameterized, tokens scope data to a user, chat length is capped, and Groq is called only server-side with a timeout and fallback. In production add a rotated secret manager, TLS, rate limiting at gateway/application level, audit logs, encryption policy, CSRF approach appropriate to the chosen auth transport, and a reviewed CORS allowlist.
