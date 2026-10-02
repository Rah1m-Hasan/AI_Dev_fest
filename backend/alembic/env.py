from app.db import Base
from app import models
target_metadata = Base.metadata
# Configure Alembic with DATABASE_URL in deployment; initial migration is retained below.
