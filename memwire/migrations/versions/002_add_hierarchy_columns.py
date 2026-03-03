"""Add hierarchy columns for multi-tenant isolation.

Revision ID: 002_add_hierarchy
Revises: 001_v1_baseline
Create Date: 2026-03-03

Adds org_id, workspace_id, app_id columns across tables for
4-level hierarchy (org > workspace > app > user). Also adds
user_id to graph_nodes and edges for per-user graph isolation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_hierarchy"
down_revision: Union[str, Sequence[str], None] = "001_v1_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hierarchy columns to all tables."""
    # --- memories ---
    op.add_column("memories", sa.Column("org_id", sa.String(), nullable=False, server_default="default"))
    op.add_column("memories", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("memories", sa.Column("app_id", sa.String(), nullable=True))
    op.create_index("ix_memories_org_id", "memories", ["org_id"])
    op.create_index("ix_memories_workspace_id", "memories", ["workspace_id"])
    op.create_index("ix_memories_app_id", "memories", ["app_id"])
    op.create_index("ix_memories_hierarchy", "memories", ["org_id", "workspace_id", "app_id", "user_id"])

    # --- graph_nodes ---
    op.add_column("graph_nodes", sa.Column("user_id", sa.String(), nullable=False, server_default="default"))
    op.add_column("graph_nodes", sa.Column("app_id", sa.String(), nullable=True))
    op.add_column("graph_nodes", sa.Column("workspace_id", sa.String(), nullable=True))

    # --- edges ---
    op.add_column("edges", sa.Column("user_id", sa.String(), nullable=False, server_default="default"))

    # --- anchors ---
    op.add_column("anchors", sa.Column("org_id", sa.String(), nullable=False, server_default="default"))
    op.add_column("anchors", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("anchors", sa.Column("app_id", sa.String(), nullable=True))

    # --- knowledge_bases ---
    op.add_column("knowledge_bases", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("knowledge_bases", sa.Column("app_id", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove hierarchy columns from all tables."""
    # --- knowledge_bases ---
    op.drop_column("knowledge_bases", "app_id")
    op.drop_column("knowledge_bases", "workspace_id")

    # --- anchors ---
    op.drop_column("anchors", "app_id")
    op.drop_column("anchors", "workspace_id")
    op.drop_column("anchors", "org_id")

    # --- edges ---
    op.drop_column("edges", "user_id")

    # --- graph_nodes ---
    op.drop_column("graph_nodes", "workspace_id")
    op.drop_column("graph_nodes", "app_id")
    op.drop_column("graph_nodes", "user_id")

    # --- memories ---
    op.drop_index("ix_memories_hierarchy", "memories")
    op.drop_index("ix_memories_app_id", "memories")
    op.drop_index("ix_memories_workspace_id", "memories")
    op.drop_index("ix_memories_org_id", "memories")
    op.drop_column("memories", "app_id")
    op.drop_column("memories", "workspace_id")
    op.drop_column("memories", "org_id")
