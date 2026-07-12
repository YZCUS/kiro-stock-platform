#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_DIR="${PROJECT_DIR:-/home/opc/projects/kiro-stock-platform}"
BACKUP_DIR="$PROJECT_DIR/backups"
IMAGE_ENV_FILE="${IMAGE_ENV_FILE:-.env.images}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
cd "$PROJECT_DIR"

[ -s .env.production ] || {
  echo "Missing .env.production" >&2
  exit 1
}
[ -s "$IMAGE_ENV_FILE" ] || {
  echo "Missing immutable image manifest: $IMAGE_ENV_FILE" >&2
  exit 1
}
python3 scripts/validate-production-env.py .env.production
python3 scripts/validate-production-env.py --images "$IMAGE_ENV_FILE"
if [ -n "${BACKUP_RETENTION_DAYS:-}" ]; then
  RETENTION_DAYS="$BACKUP_RETENTION_DAYS"
else
  RETENTION_DAYS="$(
    python3 scripts/validate-production-env.py \
      --get BACKUP_RETENTION_DAYS .env.production 2>/dev/null || printf '30'
  )"
fi
case "$RETENTION_DAYS" in
  ''|*[!0-9]*)
    echo "BACKUP_RETENTION_DAYS must be a non-negative integer" >&2
    exit 1
    ;;
esac
mkdir -p "$BACKUP_DIR"

compose() {
  docker compose -p kiro-stock-platform \
    --env-file .env.production --env-file "$IMAGE_ENV_FILE" \
    -f docker-compose.prod.yml "$@"
}

container_id="$(compose ps -q postgres)"
[ -n "$container_id" ] && [ "$(docker inspect -f '{{.State.Running}}' "$container_id")" = true ] || {
  echo "PostgreSQL service is not running" >&2
  exit 1
}

backup_file="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
backup_tmp="${backup_file}.tmp"
trap 'rm -f "$backup_tmp"' EXIT
compose exec -T postgres sh -ec \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl --clean --if-exists' \
  | gzip > "$backup_tmp"
[ -s "$backup_tmp" ]
gzip -t "$backup_tmp"
mv "$backup_tmp" "$backup_file"
trap - EXIT

config_files=(
  .env.production
  docker-compose.prod.yml
  nginx/nginx.conf
  nginx/conf.d
)
config_files+=("$IMAGE_ENV_FILE")
tar -czf "$BACKUP_DIR/config_backup_${TIMESTAMP}.tar.gz" "${config_files[@]}"

find "$BACKUP_DIR" -type f \
  \( -name 'db_backup_*.sql.gz' -o -name 'config_backup_*.tar.gz' \) \
  -mtime "+$RETENTION_DAYS" -delete

echo "Database backup verified: $backup_file"
