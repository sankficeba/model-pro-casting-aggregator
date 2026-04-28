#!/bin/sh
set -e

# Параметр $1 — режим запуска: bot (по умолчанию) или api
MODE="${1:-bot}"

echo "[entrypoint] MODE=$MODE"
echo "[entrypoint] Running database migrations..."
alembic upgrade head

case "$MODE" in
  bot)
    echo "[entrypoint] Starting bot (userbot + aiogram)..."
    exec python main.py
    ;;
  api)
    echo "[entrypoint] Starting FastAPI on :8000..."
    exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers
    ;;
  *)
    echo "[entrypoint] Unknown MODE: $MODE"
    exit 1
    ;;
esac
