"""V1 baseline schema — Qdrant-first with SQLite metadata ledger.

Revision ID: 001_v1_baseline
Revises: None
Create Date: 2026-02-26

This is the fresh v1 schema. All vectors live in Qdrant.
SQLite stores metadata, edges, anchors, and knowledge base records.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_v1_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all v1 tables."""
    # memories — metadata only (no embedding blobs)
    op.create_table(
        "memories",
        sa.Column("memory_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("agent_id", sa.String(), nullable=True, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("strength", sa.Float(), server_default="1.0"),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("node_ids_json", sa.Text(), server_default="[]"),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("access_count", sa.Integer(), server_default="0"),
    )

    # graph_nodes — metadata only (no embedding blobs)
    op.create_table(
        "graph_nodes",
        sa.Column("node_id", sa.String(), primary_key=True),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("memory_ids_json", sa.Text(), server_default="[]"),
    )

    # edges — unchanged from before
    op.create_table(
        "edges",
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("target_id", sa.String(), primary_key=True),
        sa.Column("weight", sa.Float(), server_default="0.5"),
        sa.Column("displacement_sim", sa.Float(), server_default="0.0"),
    )

    # anchors — no embedding blob
    op.create_table(
        "anchors",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("texts_json", sa.Text(), nullable=False),
    )

    # knowledge_bases — new table
    op.create_table(
        "knowledge_bases",
        sa.Column("kb_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
    )


def downgrade() -> None:
    """Drop all v1 tables."""
    op.drop_table("knowledge_bases")
    op.drop_table("anchors")
    op.drop_table("edges")
    op.drop_table("graph_nodes")
    op.drop_table("memories")
