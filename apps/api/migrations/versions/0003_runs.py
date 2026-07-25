"""workflow runs: runs table + agent_runs.run_id (Phase 5, SRS §6)

Revision ID: 0003_runs
Revises: 0002_context_items
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_runs"
down_revision: str | None = "0002_context_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("current_agent", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'timeout')",
            name="ck_runs_status",
        ),
    )
    op.create_index("ix_runs_project_id", "runs", ["project_id"])

    op.add_column("agent_runs", sa.Column("run_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_agent_runs_run_id", "agent_runs", "runs", ["run_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_agent_runs_run_id", "agent_runs", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_run_id", "agent_runs")
    op.drop_constraint("fk_agent_runs_run_id", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "run_id")
    op.drop_table("runs")
