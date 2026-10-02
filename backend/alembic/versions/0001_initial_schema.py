"""Initial Upay Coach schema.

Revision ID: 0001_initial
"""
revision = "0001_initial"
down_revision = None
def upgrade():
    # SQLAlchemy create_all is used by the portable demo bootstrap. In a production
    # Alembic runner, generate operations from app.models.Base.metadata here.
    pass
def downgrade(): pass
