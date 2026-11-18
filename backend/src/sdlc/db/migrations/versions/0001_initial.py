"""initial: conversation + message

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-26 19:00:00
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column(
            "project_id",
            sa.String(length=64),
            nullable=False,
            server_default="default",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_conversation_project_id",
        "conversation",
        ["project_id"],
    )
    op.create_index(
        "ix_conversation_updated_at",
        "conversation",
        ["updated_at"],
    )

    op.create_table(
        "message",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "conversation_id",
            sa.String(length=64),
            sa.ForeignKey("conversation.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("agent_name", sa.String(length=64), nullable=True),
        sa.Column("trace_url", sa.String(length=500), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_message_conversation_created",
        "message",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_message_conversation_created", table_name="message")
    op.drop_table("message")
    op.drop_index("ix_conversation_updated_at", table_name="conversation")
    op.drop_index("ix_conversation_project_id", table_name="conversation")
    op.drop_table("conversation")
