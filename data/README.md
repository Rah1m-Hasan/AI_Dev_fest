# Data strategy

The running prototype uses **only self-generated, synthetic demo data**. It does not include, claim access to, or model real upay customer records. `backend/app/services/seed.py` produces four demo personas and 90 days of transaction history with income cycles, recurring utility/subscription expenses, food, transport, weekend and month-end variation. The data is marked `source=synthetic_demo` in the database.

`data/external/` is reserved for carefully reviewed public sources. No external raw dataset is packaged or downloaded automatically. This avoids redistributing a large data file or relying on an ambiguous third-party mirror. See `docs/data-sources.md` for the research decision and reproduction constraints.

For a larger offline evaluation dataset, extend `scripts/generate_synthetic_data.py` using a fixed seed and write independent train/validation/test splits below `data/processed/`; do not use a test split to tune an algorithm.
