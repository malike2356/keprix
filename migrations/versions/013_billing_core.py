"""Alembic migration: billing customers, subscriptions, invoices, seats."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "013_billing_core"
down_revision = "012_data_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_customers",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("vat_id", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("product_id", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("seats", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("feature_flags", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_billing_subscriptions_user", "billing_subscriptions", ["user_id"])

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("tax_amount", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("stripe_invoice_id", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_billing_invoices_user", "billing_invoices", ["user_id"])

    op.create_table(
        "billing_seats",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'member'")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'invited'")),
        sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_billing_seats_owner", "billing_seats", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_seats_owner", table_name="billing_seats")
    op.drop_table("billing_seats")
    op.drop_index("ix_billing_invoices_user", table_name="billing_invoices")
    op.drop_table("billing_invoices")
    op.drop_index("ix_billing_subscriptions_user", table_name="billing_subscriptions")
    op.drop_table("billing_subscriptions")
    op.drop_table("billing_customers")
