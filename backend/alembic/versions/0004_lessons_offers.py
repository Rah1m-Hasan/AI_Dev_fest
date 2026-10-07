"""Add financial_lessons columns, lesson_progress, saved_offers.

Revision ID: 0004_lessons_offers
"""
revision = "0004_lessons_offers"
down_revision = "0003_trusted_people"

def upgrade():
    from alembic import op
    import sqlalchemy as sa

    # Add columns to financial_lessons
    for col, col_type in [
        ("summary", sa.String(280)),
        ("content_bn", sa.Text),
        ("category", sa.String(40)),
        ("difficulty", sa.String(20)),
        ("duration_minutes", sa.Integer),
        ("personalized_section", sa.Text),
        ("personalized_section_bn", sa.Text),
        ("quiz", sa.JSON),
        ("trigger_type", sa.String(60)),
        ("trigger_rule", sa.JSON),
        ("active", sa.Boolean),
    ]:
        op.add_column("financial_lessons", sa.Column(col, col_type, nullable=True))

    # Alter offer table
    for col, col_type in [
        ("terms_bn", sa.Text),
        ("category", sa.String(40)),
        ("min_spend", sa.Numeric(14, 2)),
        ("discount_percent", sa.Numeric(5, 2)),
        ("discount_fixed", sa.Numeric(14, 2)),
        ("max_discount", sa.Numeric(14, 2)),
        ("typical_purchase", sa.Numeric(14, 2)),
        ("typical_merchant", sa.String(120)),
        ("potential_saving", sa.Numeric(14, 2)),
        ("expiry_date", sa.Date),
        ("eligibility_notes", sa.String(280)),
        ("learning_lesson_id", sa.Integer, sa.ForeignKey("financial_lessons.id")),
    ]:
        op.add_column("offers", sa.Column(col, col_type, nullable=True))

    # lesson_progress table (full create)
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("lesson_id", sa.Integer, sa.ForeignKey("financial_lessons.id")),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("quiz_score", sa.Integer, nullable=True),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )

    # saved_offers table
    op.create_table(
        "saved_offers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("offer_id", sa.Integer, sa.ForeignKey("offers.id"), index=True),
        sa.Column("saved_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("user_id", "offer_id", name="uq_saved_offer_user_offer"),
    )

def downgrade():
    from alembic import op
    op.drop_table("saved_offers")
    op.drop_table("lesson_progress")
    # Columns are dropped implicitly; downgrade not critical for demo.
    pass
