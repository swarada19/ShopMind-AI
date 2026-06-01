"""Initial schema — all ShopMind AI tables

Revision ID: 001
Revises:
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── user_preferences ──────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("max_budget", sa.Float, nullable=True),
        sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("preferred_brands", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("preferred_categories", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── products ──────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("original_price", sa.Float, nullable=True),
        sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("rating", sa.Float, nullable=True),
        sa.Column("review_count", sa.Integer, nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("source", sa.String(50), server_default="serpapi", nullable=False),
        sa.Column("features", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("trust_score", sa.Float, nullable=True),
        sa.Column("search_query", sa.String(500), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_products_external_id", "products", ["external_id"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_search_query", "products", ["search_query"])

    # ── watchlist ────────────────────────────────────────────────────────
    op.create_table(
        "watchlist",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_title", sa.String(500), nullable=False),
        sa.Column("product_url", sa.Text, nullable=True),
        sa.Column("product_query", sa.String(500), nullable=False),
        sa.Column("current_price", sa.Float, nullable=True),
        sa.Column("target_price", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("last_checked_price", sa.Float, nullable=True),
        sa.Column("alert_sent_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_watchlist_user_id", "watchlist", ["user_id"])

    # ── search_history ───────────────────────────────────────────────────
    op.create_table(
        "search_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_query", sa.String(500), nullable=False),
        sa.Column("product_query", sa.String(500), nullable=True),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("results_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_search_history_user_id", "search_history", ["user_id"])

    # ── alert_logs ───────────────────────────────────────────────────────
    op.create_table(
        "alert_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("watchlist_item_id", sa.String(36), sa.ForeignKey("watchlist.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_title", sa.String(500), nullable=False),
        sa.Column("triggered_price", sa.Float, nullable=True),
        sa.Column("target_price", sa.Float, nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("message_body", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="sent", nullable=False),
        sa.Column("twilio_sid", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alert_logs_user_id", "alert_logs", ["user_id"])
    op.create_index("ix_alert_logs_watchlist_item_id", "alert_logs", ["watchlist_item_id"])


def downgrade() -> None:
    op.drop_table("alert_logs")
    op.drop_table("search_history")
    op.drop_table("watchlist")
    op.drop_table("products")
    op.drop_table("user_preferences")
    op.drop_table("users")
