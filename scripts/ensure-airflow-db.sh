#!/bin/sh
set -eu

case "${AIRFLOW_DB:-}" in
  ""|*[!A-Za-z0-9_]*)
    echo "AIRFLOW_DB must contain only letters, numbers, and underscores" >&2
    exit 1
    ;;
esac

export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
max_attempts="${AIRFLOW_DB_PREPARE_MAX_ATTEMPTS:-60}"
case "$max_attempts" in
  ""|*[!0-9]*|0)
    echo "AIRFLOW_DB_PREPARE_MAX_ATTEMPTS must be a positive integer" >&2
    exit 1
    ;;
esac

attempt=1
until pg_isready -h postgres -U "${POSTGRES_USER}" -d postgres >/dev/null 2>&1; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "PostgreSQL did not become ready after $max_attempts attempts" >&2
    pg_isready -h postgres -U "${POSTGRES_USER}" -d postgres >&2 || true
    exit 1
  fi
  sleep 2
  attempt=$((attempt + 1))
done

exists="$(
  psql -h postgres -U "${POSTGRES_USER}" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${AIRFLOW_DB}'"
)"
if [ "$exists" != "1" ]; then
  psql -h postgres -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"${AIRFLOW_DB}\""
fi
