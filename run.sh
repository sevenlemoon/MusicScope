#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.logs"
mkdir -p "$LOG_DIR"

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

echo "Starting PostgreSQL..."
if docker compose -f "$ROOT_DIR/docker-compose.yml" up -d postgres; then
  echo "PostgreSQL is running."
else
  echo "PostgreSQL could not be started by Docker Compose."
fi

if port_in_use 8000; then
  echo "Backend is already running on port 8000."
else
  (
    cd "$ROOT_DIR/apps/api"
    exec "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --reload --port 8000
  ) >>"$LOG_DIR/backend.log" 2>&1 &
  echo $! >"$LOG_DIR/backend.pid"
  echo "Backend started; logs: .logs/backend.log"
fi

if port_in_use 3000; then
  echo "Frontend is already running on port 3000."
else
  if [[ -f "$ROOT_DIR/apps/web/.next/BUILD_ID" ]]; then
    FRONTEND_COMMAND=(npm start -- --hostname 127.0.0.1)
  else
    FRONTEND_COMMAND=(npm run dev -- --hostname 127.0.0.1)
  fi
  (
    cd "$ROOT_DIR/apps/web"
    exec "${FRONTEND_COMMAND[@]}"
  ) >>"$LOG_DIR/frontend.log" 2>&1 &
  echo $! >"$LOG_DIR/frontend.pid"
  echo "Frontend started; logs: .logs/frontend.log"
fi

sleep 2
if curl --silent --show-error --fail --max-time 3 http://127.0.0.1:8000/health >/dev/null; then
  BACKEND_STATUS="healthy"
else
  BACKEND_STATUS="not healthy yet; see .logs/backend.log"
fi

echo
echo "MusicScope is running"
echo
echo "Frontend:"
echo "http://localhost:3000"
echo
echo "Backend:"
echo "http://127.0.0.1:8000"
echo
echo "API docs:"
echo "http://127.0.0.1:8000/docs"
echo
echo "Logs:"
echo ".logs/backend.log"
echo ".logs/frontend.log"
echo
echo "Backend health: $BACKEND_STATUS"
