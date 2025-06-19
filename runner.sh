#!/usr/bin/env bash
set -euo pipefail

# Load environment variables from .env if it exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# Create and activate Python 3.10 virtual environment, then install Python dependencies
if [ ! -d ".venv" ]; then
  echo "Creating Python 3.10 virtual environment in .venv..."
  python3.10 -m venv .venv
else
  echo "Using existing Python 3.10 virtual environment in .venv..."
fi

echo "Activating virtual environment..."
source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "Installing pydot without dependencies..."
pip install --no-deps -r requirements-pydot.txt  #install pydot without dependencies as it conflicts with flink and needs the oldest possible version of it
echo "Python dependencies installed."

# Remove old versions of specified files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
for entry in "frontend/src/declare_model.png:declare_model.png" "processor/src/rules/rules.json:rules.json"; do
  IFS=':' read -r rel_path description <<< "$entry"
  file="${SCRIPT_DIR}/${rel_path}"
  if [[ -f "$file" ]]; then
    printf 'Removing old %s at %s...\n' "$description" "$file"
    rm -f -- "$file"
  fi
done

# Delete the model picture when the program is shut down
cleanup_on_exit() {
  declare_model_path="${SCRIPT_DIR}/frontend/src/declare_model.png"
  if [[ -f "$declare_model_path" ]]; then
    echo "Script interrupted! Removing declare_model.png due to interruption..."
    rm -f -- "$declare_model_path"
  fi
  exit 1
}
trap cleanup_on_exit SIGINT SIGTERM SIGTSTP

# Free up specified ports
for PORT in "${PORT_FRONTEND}" "${PORT_FLINK}" "${PORT_KAFKA_UI}"; do
  echo "Checking for processes using port ${PORT}..."
  PIDS=$(sudo lsof -t -i :"${PORT}" || true)
  if [[ -n "${PIDS}" ]]; then
    echo "Killing process(es) on port ${PORT}: ${PIDS}"
    for pid in ${PIDS}; do
      sudo kill -9 "${pid}" && echo "→ Killed ${pid}"
    done
  else
    echo "→ No process found on port ${PORT}."
  fi
done

# Stop and clean up containers from previous run
echo "Stopping and removing containers from previous run..."
docker compose down -v --remove-orphans

# Start all services via Docker Compose
echo "Starting Docker Compose services..."
docker compose up -d

# Ports for all services
FRONTEND_URL="http://localhost:${PORT_FRONTEND}"
FLINK_UI_URL="http://localhost:${PORT_FLINK}"
KAFKA_UI_URL="http://localhost:${PORT_KAFKA_UI}"

# Wait for frontend and Kafka UI ports to be open
for service in "frontend:${PORT_FRONTEND}" "Kafka UI:${PORT_KAFKA_UI}"; do
  name="${service%%:*}"
  port="${service##*:}"
  echo "Waiting for ${name} on port ${port}..."
  until nc -z localhost "${port}"; do
    sleep 1
  done
done

# Open URLs for frontend and Kafka UI
echo "Opening all service UIs in your browser ..."
for url in "${FRONTEND_URL}" "${KAFKA_UI_URL}"; do
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" &
  elif command -v open >/dev/null 2>&1; then
    open "$url" &
  elif command -v explorer.exe >/dev/null 2>&1; then
    explorer.exe "$url" &
  else
    echo "⚠️ Couldn't find xdg-open, open or explorer; please open $url manually."
  fi
done

# Run processor module in background and save its PID
python3 -m processor.src.main & PROCESSOR_PID=$!

# Start a background task to wait for Flink UI and open it in the browser
(
  echo "Waiting for Flink UI on port ${PORT_FLINK}..."
  until nc -z localhost "${PORT_FLINK}"; do
    sleep 1
  done
  echo "Flink UI is up. Opening in browser..."
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${FLINK_UI_URL}" &
  elif command -v open >/dev/null 2>&1; then
    open "${FLINK_UI_URL}" &
  elif command -v explorer.exe >/dev/null 2>&1; then
    explorer.exe "${FLINK_UI_URL}" &
  else
    echo "⚠️ Couldn't find a suitable command to open URLs; please open ${FLINK_UI_URL} manually."
  fi
) &
# Wait for the processor module to finish before exiting the script
wait $PROCESSOR_PID