"""Generate the database-backed synthetic Upay-style demo data.

The API seeds four representative demo users (90 days, realistic recurring
payments/income cycles). This script is the explicit reproducible entry point.
"""
from app.db import Base, engine, SessionLocal
from app.services.seed import seed
Base.metadata.create_all(engine)
with SessionLocal() as db: seed(db)
print("Synthetic demo seed completed. No real customer or upay data was used.")
