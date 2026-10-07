"""Add persisted helper relationships, activity, and assistance requests.

Revision ID: 0002_helper_mode
Revises: 0001_initial
"""
revision = "0002_helper_mode"
down_revision = "0001_initial"

def upgrade():
    from alembic import op
    from app.models import UserPhone, HelperRelationship, HelperActivity, HelperAssistanceRequest
    bind = op.get_bind()
    UserPhone.__table__.create(bind=bind, checkfirst=True)
    HelperRelationship.__table__.create(bind=bind, checkfirst=True)
    HelperActivity.__table__.create(bind=bind, checkfirst=True)
    HelperAssistanceRequest.__table__.create(bind=bind, checkfirst=True)

def downgrade():
    from alembic import op
    from app.models import UserPhone, HelperRelationship, HelperActivity, HelperAssistanceRequest
    bind = op.get_bind()
    HelperAssistanceRequest.__table__.drop(bind=bind, checkfirst=True)
    HelperActivity.__table__.drop(bind=bind, checkfirst=True)
    HelperRelationship.__table__.drop(bind=bind, checkfirst=True)
    UserPhone.__table__.drop(bind=bind, checkfirst=True)
