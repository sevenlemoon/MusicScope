#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.logs"

stop_recorded_process() {
  local name="$1"
  local pid_file="$2"
  local expected_dir="$3"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if [[ ! "$pid" =~ ^[0-9]+$ ]] || ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    echo "Removed stale $name PID file."
    return
  fi

  local process_dir
  process_dir="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
  if [[ "$process_dir" != "$expected_dir" ]]; then
    echo "Did not stop PID $pid: it is not the recorded MusicScope $name process."
    return
  fi

  if kill "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    echo "Stopped $name process (PID $pid)."
  else
    echo "Could not stop recorded $name process (PID $pid)."
  fi
}

if [[ -d "$LOG_DIR" ]]; then
  stop_recorded_process "backend" "$LOG_DIR/backend.pid" "$ROOT_DIR/apps/api"
  stop_recorded_process "frontend" "$LOG_DIR/frontend.pid" "$ROOT_DIR/apps/web"
fi

echo "MusicScope application processes stopped."
echo "PostgreSQL remains running."
