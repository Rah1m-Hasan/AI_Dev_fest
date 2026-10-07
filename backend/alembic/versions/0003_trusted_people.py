"""Persist verification and activity for Trusted People.

Revision ID: 0003_trusted_people
Revises: 0002_helper_mode
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_trusted_people"
down_revision = "0002_helper_mode"

def upgrade():
    # 0001 uses metadata.create_all for this compact demo, so a fresh database
    # can already have the current columns. Keep this migration safe in both
    # fresh and pre-Trusted-People databases.
    inspector = sa.inspect(op.get_bind())
    contact_columns = {column["name"] for column in inspector.get_columns("trusted_contacts")}
    if "normalized_phone" not in contact_columns:
        with op.batch_alter_table("trusted_contacts") as batch:
            batch.add_column(sa.Column("normalized_phone", sa.String(length=20), nullable=True))
            batch.add_column(sa.Column("notes", sa.String(length=280), nullable=True))
            batch.add_column(sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="unverified"))
            batch.add_column(sa.Column("verified_at", sa.DateTime(), nullable=True))
            batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
            batch.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE trusted_contacts SET normalized_phone = CASE WHEN phone_number LIKE '0%' THEN '880' || substr(phone_number, 2) ELSE phone_number END")
        with op.batch_alter_table("trusted_contacts") as batch:
            batch.alter_column("normalized_phone", nullable=False)
            batch.create_unique_constraint("uq_trusted_contact_user_phone", ["user_id", "normalized_phone"])
            batch.create_index("ix_trusted_contacts_normalized_phone", ["normalized_phone"])
            batch.create_index("ix_trusted_contacts_verification_status", ["verification_status"])
            batch.create_index("ix_trusted_contacts_archived_at", ["archived_at"])
    tables = set(inspector.get_table_names())
    if "payment_requests" not in tables: op.create_table("payment_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trusted_contact_id", sa.Integer(), sa.ForeignKey("trusted_contacts.id"), nullable=False), sa.Column("recipient_name", sa.String(80), nullable=False),
        sa.Column("recipient_phone", sa.String(20), nullable=False), sa.Column("amount", sa.Numeric(14, 2), nullable=False), sa.Column("note", sa.String(140)),
        sa.Column("status", sa.String(24), nullable=False, server_default="requested"), sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    if "payment_requests" not in tables:
        op.create_index("ix_payment_requests_user_id", "payment_requests", ["user_id"])
        op.create_index("ix_payment_requests_trusted_contact_id", "payment_requests", ["trusted_contact_id"])
    if "trusted_contact_audit" not in tables: op.create_table("trusted_contact_audit",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("trusted_contact_id", sa.Integer(), sa.ForeignKey("trusted_contacts.id")), sa.Column("event_type", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    if "trusted_contact_audit" not in tables:
        op.create_index("ix_trusted_contact_audit_user_id", "trusted_contact_audit", ["user_id"])
        op.create_index("ix_trusted_contact_audit_contact_id", "trusted_contact_audit", ["trusted_contact_id"])

def downgrade():
    op.drop_table("trusted_contact_audit")
    op.drop_table("payment_requests")
    with op.batch_alter_table("trusted_contacts") as batch:
        batch.drop_constraint("uq_trusted_contact_user_phone", type_="unique")
        batch.drop_column("archived_at"); batch.drop_column("updated_at"); batch.drop_column("verified_at")
        batch.drop_column("verification_status"); batch.drop_column("notes"); batch.drop_column("normalized_phone")
