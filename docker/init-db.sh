#!/bin/bash
set -e

# Create agno schema for Agno memory/knowledge tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE SCHEMA IF NOT EXISTS agno;
    GRANT ALL ON SCHEMA agno TO $POSTGRES_USER;
EOSQL

echo "memwire: pgvector extension and agno schema created."
