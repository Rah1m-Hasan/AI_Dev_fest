"""Persist draft and accepted monthly plan state.

Revision ID: 0005_plan_state
Revises: 0004_lessons_offers
"""
revision = "0005_plan_state"
down_revision = "0004_lessons_offers"

def upgrade():
    from alembic import op
    import sqlalchemy as sa
    op.create_table(
        "plan_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="recommended"),
        sa.Column("essentials", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("flexible", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("savings", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("safety_buffer", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("budget_id", sa.Integer(), sa.ForeignKey("budgets.id"), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

def downgrade():
    from alembic import op
    op.drop_table("plan_states")
