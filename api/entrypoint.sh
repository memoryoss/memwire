#!/usr/bin/env bash
set -e

show_help() {
    echo "Usage: ./entrypoint.sh [OPTIONS]"
    echo "  --migrate   Run Alembic migrations before starting"
    echo "  --dev       Run with hot-reload (development mode)"
    echo "  --help      Show this message"
}

migrate=false
dev=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --migrate) migrate=true ;;
        --dev)     dev=true ;;
        --help|-h) show_help; exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
    shift
done

if [ "$migrate" = true ]; then
    echo "▶ Running database migrations..."
    python -m alembic upgrade head
    echo "✓ Migrations complete"
fi

if [ "$dev" = true ]; then
    echo "▶ Starting in development mode (hot-reload)..."
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level debug
else
    echo "▶ Starting in production mode..."
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 2 \
        --log-level info
fi
