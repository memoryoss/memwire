"""Initial schema — memwire tables

Revision ID: 0001
Create Date: 2026-02-22

Sets up:
  - pgvector extension
  - agno schema  (owned by Agno; memory tables are created dynamically)
  - memwire schema
    - memwire.api_keys      — API key store
    - memwire.kb_documents  — knowledge-base document registry
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS agno")
    op.execute("CREATE SCHEMA IF NOT EXISTS memwire")
    op.execute("GRANT ALL ON SCHEMA agno TO CURRENT_USER")
    op.execute("GRANT ALL ON SCHEMA memwire TO CURRENT_USER")

    # API keys — used by /v1/api-keys router
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memwire.api_keys (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            description  TEXT,
            key_hash     TEXT NOT NULL UNIQUE,
            key_prefix   TEXT NOT NULL,
            created_at   TIMESTAMPTZ DEFAULT NOW(),
            last_used_at TIMESTAMPTZ
        )
        """
    )

    # Knowledge-base document registry — used by /v1/knowledge router
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memwire.kb_documents (
            doc_id       TEXT PRIMARY KEY,
            agent_id     TEXT NOT NULL,
            doc_name     TEXT NOT NULL,
            source_type  TEXT NOT NULL,
            source       TEXT,
            chunk_count  INT DEFAULT 0,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS kb_documents_agent_idx ON memwire.kb_documents (agent_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS memwire.kb_documents_agent_idx")
    op.execute("DROP TABLE IF EXISTS memwire.kb_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS memwire.api_keys CASCADE")
    op.execute("DROP SCHEMA IF EXISTS memwire CASCADE")
    op.execute("DROP SCHEMA IF EXISTS agno CASCADE")
