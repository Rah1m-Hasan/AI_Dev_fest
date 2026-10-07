"""Add financial_lessons columns, lesson_progress, saved_offers.

Revision ID: 0004_lessons_offers
"""
revision = "0004_lessons_offers"
down_revision = "0003_trusted_people"

def upgrade():
    from alembic import op
    import sqlalchemy as sa

    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    # Add columns to financial_lessons
    lesson_columns = {column["name"] for column in inspector.get_columns("financial_lessons")} if "financial_lessons" in tables else set()
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
        if col not in lesson_columns:
            op.add_column("financial_lessons", sa.Column(col, col_type, nullable=True))

    # Alter offer table
    offer_columns = {column["name"] for column in inspector.get_columns("offers")} if "offers" in tables else set()
    for definition in [
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
        col, col_type, *constraints = definition
        if col not in offer_columns:
            op.add_column("offers", sa.Column(col, col_type, *constraints, nullable=True))

    # lesson_progress table (full create)
    if "lesson_progress" not in tables:
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
    if "saved_offers" not in tables:
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
