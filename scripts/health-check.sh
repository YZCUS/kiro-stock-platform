#!/bin/sh
set -eu

PROJECT_DIR="${PROJECT_DIR:-/home/opc/projects/kiro-stock-platform}"
cd "$PROJECT_DIR"

if [ ! -s .env.production ]; then
  echo "Missing .env.production" >&2
  exit 1
fi
if [ ! -s .env.images ]; then
  echo "Missing immutable .env.images" >&2
  exit 1
fi
python3 scripts/validate-production-env.py .env.production
python3 scripts/validate-production-env.py --images .env.images
production_base_url="$(
  python3 scripts/validate-production-env.py \
    --get PRODUCTION_BASE_URL .env.production
)"
production_hostname="$(
  python3 -c \
    'import sys; from urllib.parse import urlparse; print(urlparse(sys.argv[1]).hostname or "")' \
    "$production_base_url"
)"

compose() {
  docker compose -p kiro-stock-platform \
    --env-file .env.production --env-file .env.images \
    -f docker-compose.prod.yml "$@"
}

running_services="
postgres redis backend frontend qlib-prediction-service
order-execution-worker broker-sync-worker market-data-worker
bar-aggregation-worker data-validation-worker indicator-worker
strategy-worker notification-worker airflow-webserver airflow-scheduler nginx
"
completed_services="airflow-db-prepare backend-migrate qlib-artifact-prepare airflow-init"

check_service_running() {
  service="$1"
  container_id="$(compose ps -q "$service")"
  [ -n "$container_id" ] || return 1
  [ "$(docker inspect -f '{{.State.Running}}' "$container_id")" = "true" ] || return 1
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
  [ "$health" = "healthy" ] || [ "$health" = "none" ]
}

check_service_completed() {
  service="$1"
  container_id="$(compose ps -aq "$service")"
  [ -n "$container_id" ] || return 1
  [ "$(docker inspect -f '{{.State.ExitCode}}' "$container_id")" = "0" ]
}

check_runtime() {
  for service in $running_services; do
    check_service_running "$service" || return 1
  done
  for service in $completed_services; do
    check_service_completed "$service" || return 1
  done
  compose exec -T backend curl -fsS http://localhost:8000/health >/dev/null
  compose exec -T frontend wget -q --spider http://localhost:3000/api/health
  compose exec -T qlib-prediction-service python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8090/health', timeout=5)"
  compose exec -T airflow-webserver curl -fsS http://localhost:8080/health >/dev/null
  curl --resolve "${production_hostname}:443:127.0.0.1" \
    -fsS "$production_base_url/health" >/dev/null
}

attempt=1
while [ "$attempt" -le 30 ]; do
  if check_runtime; then
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "Platform did not become healthy within 300 seconds" >&2
    compose ps >&2
    exit 1
  fi
  sleep 10
  attempt=$((attempt + 1))
done

compose exec -T postgres sh -ec \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
compose exec -T redis sh -ec \
  'redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG'

disk_usage="$(df -P / | awk 'NR == 2 {gsub("%", "", $5); print $5}')"
if [ "$disk_usage" -ge 90 ]; then
  echo "Disk usage is critical: ${disk_usage}%" >&2
  exit 1
fi

echo "All production services and health endpoints are healthy."
