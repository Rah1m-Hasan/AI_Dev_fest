"""Initial Upay Coach schema.

Revision ID: 0001_initial
"""
revision = "0001_initial"
down_revision = None
def upgrade():
    # The compact demo schema is metadata-driven and portable across SQLite and
    # PostgreSQL. This makes `alembic upgrade head` functional rather than a no-op.
    from alembic import op
    from app.db import Base
    from app import models  # noqa: F401 - registers all mapped tables
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    from alembic import op
    from app.db import Base
    from app import models  # noqa: F401
    Base.metadata.drop_all(bind=op.get_bind())
