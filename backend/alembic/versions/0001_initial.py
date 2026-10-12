"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "farmers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("shop_name", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, index=True),
        sa.Column("unit", sa.String(16), nullable=False, server_default="шт"),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("produced_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("description_len", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views_14d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cart_14d", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=False, index=True),
        sa.Column("ext_ref", sa.String(32), nullable=False),
        sa.Column("segment", sa.String(32), nullable=False, server_default="repeat"),
        sa.Column("first_order_at", sa.Date(), nullable=False),
        sa.Column("last_order_at", sa.Date(), nullable=False),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("description", sa.String(512), nullable=False, server_default=""),
        sa.Column("discount_pct", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("starts_at", sa.Date(), nullable=False),
        sa.Column("ends_at", sa.Date(), nullable=False),
        sa.Column("joined", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_revenue", sa.Float(), nullable=True),
        sa.Column("result_uplift_pct", sa.Float(), nullable=True),
    )
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("day", sa.Date(), nullable=False, index=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=False),
        sa.Column("promo_id", sa.Integer(), sa.ForeignKey("promotions.id"), nullable=True),
    )
    op.create_table(
        "actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("farmer_id", sa.Integer(), sa.ForeignKey("farmers.id"), nullable=False, index=True),
        sa.Column("day", sa.Date(), nullable=False, index=True),
        sa.Column("rule_key", sa.String(64), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("segment", sa.String(32), nullable=True),
        sa.Column("facts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("effect_weekly", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("texts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("texts_source", sa.String(16), nullable=False, server_default="template"),
        sa.Column("status", sa.String(16), nullable=False, server_default="proposed", index=True),
        sa.Column("rejection_reason", sa.String(256), nullable=True),
        sa.Column("feedback", sa.String(16), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("actions")
    op.drop_table("sales")
    op.drop_table("promotions")
    op.drop_table("clients")
    op.drop_table("products")
    op.drop_table("farmers")
