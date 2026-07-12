#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/opc/projects/kiro-stock-platform}"
BACKUP_DIR="$PROJECT_DIR/backups"
cd "$PROJECT_DIR"
python3 scripts/validate-production-env.py .env.production
python3 scripts/validate-production-env.py --images .env.images

compose() {
  docker compose -p kiro-stock-platform \
    --env-file .env.production --env-file .env.images \
    -f docker-compose.prod.yml "$@"
}

backup_file="${1:-$(ls -1t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | head -1)}"
[ -s "$backup_file" ] || {
  echo "Backup file not found" >&2
  exit 1
}
gzip -t "$backup_file"

printf 'Restore %s? Type yes: ' "$backup_file"
read -r confirmation
[ "$confirmation" = yes ] || exit 0

app_services="backend order-execution-worker broker-sync-worker market-data-worker bar-aggregation-worker data-validation-worker indicator-worker strategy-worker notification-worker qlib-prediction-service airflow-webserver airflow-scheduler"
restore_phase="before-stop"

handle_restore_failure() {
  status=$?
  if [ "$status" -eq 0 ]; then
    return
  fi
  if [ "$restore_phase" = "sql-restore" ]; then
    echo "Restore transaction failed; the original database was rolled back. Restarting the previous runtime." >&2
    if ! compose up -d $app_services; then
      echo "Previous runtime restart also failed; manual recovery is required." >&2
    fi
  else
    echo "Restore failed during phase '$restore_phase'; services remain stopped or unhealthy for manual recovery." >&2
  fi
  exit "$status"
}

trap handle_restore_failure EXIT
compose stop $app_services
restore_phase="sql-restore"
gzip -dc "$backup_file" | compose exec -T postgres sh -ec \
  'psql -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
restore_phase="migration"
compose run --rm -T backend-migrate
restore_phase="startup"
compose up -d $app_services
restore_phase="health-check"
bash scripts/health-check.sh
trap - EXIT
