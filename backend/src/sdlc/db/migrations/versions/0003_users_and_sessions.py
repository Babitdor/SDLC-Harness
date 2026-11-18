"""users + sessions + conversation ownership

Revision ID: 0003_users_and_sessions
Revises: 0002_add_reasoning
Create Date: 2026-10-24 10:00:00

Single-user phase is over. No backfill: ``conversation.user_id`` stays NULL
for every pre-auth row, and every read path filters on ``user_id``, so those
conversations are invisible rather than reassigned to whoever registers first.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_users_and_sessions"
down_revision: str | None = "0002_add_reasoning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Functional index, not a UNIQUE constraint: "A@x.com" and "a@x.com" must
    # be the same account, and only lower() expresses that in Postgres.
    op.execute("CREATE UNIQUE INDEX ux_app_user_email_lower ON app_user (lower(email))")

    op.create_table(
        "user_session",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.String(length=200), server_default="", nullable=False),
        sa.Column("ip", sa.String(length=64), server_default="", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])
    op.create_index("ix_user_session_expires_at", "user_session", ["expires_at"])

    op.add_column("conversation", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index("ix_conversation_user_id", "conversation", ["user_id"])
    op.create_index(
        "ix_conversation_user_updated", "conversation", ["user_id", "updated_at"]
    )
    op.create_foreign_key(
        "conversation_user_id_fkey",
        "conversation",
        "app_user",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("conversation_user_id_fkey", "conversation", type_="foreignkey")
    op.drop_index("ix_conversation_user_updated", table_name="conversation")
    op.drop_index("ix_conversation_user_id", table_name="conversation")
    op.drop_column("conversation", "user_id")
    op.drop_index("ix_user_session_expires_at", table_name="user_session")
    op.drop_index("ix_user_session_user_id", table_name="user_session")
    op.drop_table("user_session")
    op.execute("DROP INDEX ux_app_user_email_lower")
    op.drop_table("app_user")
