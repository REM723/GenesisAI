"""context memory: context_items table (Phase 3, SRS §2)

Revision ID: 0002_context_items
Revises: 0001_init
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_context_items"
down_revision: str | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "kind IN ('requirement', 'decision', 'artifact')", name="ck_context_items_kind"
        ),
    )
    op.create_index("ix_context_items_project_id", "context_items", ["project_id"])


def downgrade() -> None:
    op.drop_table("context_items")
