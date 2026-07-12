#!/usr/bin/env python3
"""Validate production secrets and internal Docker connection URLs."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse

REQUIRED_KEYS = {
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "APP_ENVIRONMENT",
    "APP_DEBUG",
    "DATABASE_URL",
    "REDIS_PASSWORD",
    "REDIS_URL",
    "SECURITY_SECRET_KEY",
    "SECURITY_CORS_ORIGINS",
    "INTERNAL_API_TOKEN",
    "AIRFLOW_FERNET_KEY",
    "AIRFLOW_SECRET_KEY",
    "AIRFLOW_DATABASE_URL",
    "AIRFLOW_REDIS_URL",
    "AIRFLOW_ADMIN_PASSWORD",
    "QLIB_INTERNAL_TOKEN",
    "NEXT_PUBLIC_API_URL",
    "PRODUCTION_BASE_URL",
    "NEXT_PUBLIC_WS_URL",
    "NEXT_PUBLIC_MARKET_WS_URL",
}

REQUIRED_IMAGE_KEYS = {
    "BACKEND_IMAGE",
    "FRONTEND_IMAGE",
    "AIRFLOW_IMAGE",
    "QLIB_IMAGE",
}
IMMUTABLE_IMAGE_PATTERN = re.compile(r"^\S+@sha256:[0-9a-fA-F]{64}$")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} is not KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def _validate_url(
    values: dict[str, str],
    key: str,
    *,
    schemes: set[str],
    host: str,
    port: int,
    database: str,
    password_key: str,
    username_key: str | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        parsed = urlparse(values.get(key, ""))
        parsed_host = parsed.hostname
        parsed_port = parsed.port
    except ValueError:
        return [f"{key} must be a valid connection URL"]
    if parsed.scheme not in schemes:
        errors.append(f"{key} must use one of: {', '.join(sorted(schemes))}")
    if parsed_host != host:
        errors.append(f"{key} must use Docker host {host}")
    if parsed_port != port:
        errors.append(f"{key} must use port {port}")
    if parsed.path.lstrip("/") != database:
        errors.append(f"{key} must select {database}")
    if username_key is not None:
        expected_username = values.get(username_key)
        if not parsed.username:
            errors.append(f"{key} must include a username")
        elif unquote(parsed.username) != expected_username:
            errors.append(f"{key} username does not match {username_key}")
    if parsed.password is None:
        errors.append(f"{key} must include a URL-encoded password")
    elif unquote(parsed.password) != values.get(password_key):
        errors.append(f"{key} password does not match {password_key}")
    return errors


def validate(values: dict[str, str]) -> list[str]:
    errors = [
        f"{key} is required" for key in sorted(REQUIRED_KEYS) if not values.get(key)
    ]

    for key, value in values.items():
        if "CHANGE_THIS" in value or "yourdomain.com" in value:
            errors.append(f"{key} still contains a placeholder")

    for key in (
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "SECURITY_SECRET_KEY",
        "INTERNAL_API_TOKEN",
        "AIRFLOW_SECRET_KEY",
        "AIRFLOW_ADMIN_PASSWORD",
        "QLIB_INTERNAL_TOKEN",
    ):
        if values.get(key) and len(values[key]) < 24:
            errors.append(f"{key} must be at least 24 characters")

    if values.get("INTERNAL_API_TOKEN") == values.get("QLIB_INTERNAL_TOKEN"):
        errors.append("INTERNAL_API_TOKEN and QLIB_INTERNAL_TOKEN must be distinct")
    if values.get("APP_ENVIRONMENT", "").lower() != "production":
        errors.append("APP_ENVIRONMENT must be production")
    if values.get("APP_DEBUG", "").lower() != "false":
        errors.append("APP_DEBUG must be false")

    fernet_key = values.get("AIRFLOW_FERNET_KEY", "")
    try:
        decoded_fernet_key = base64.b64decode(
            fernet_key.encode(),
            altchars=b"-_",
            validate=True,
        )
        if len(decoded_fernet_key) != 32:
            raise ValueError
    except Exception:
        errors.append("AIRFLOW_FERNET_KEY must encode exactly 32 bytes")

    postgres_db = values.get("POSTGRES_DB", "")
    airflow_db = values.get("AIRFLOW_DB", "airflow")
    errors.extend(
        _validate_url(
            values,
            "DATABASE_URL",
            schemes={"postgresql", "postgresql+asyncpg"},
            host="postgres",
            port=5432,
            database=postgres_db,
            password_key="POSTGRES_PASSWORD",
            username_key="POSTGRES_USER",
        )
    )
    errors.extend(
        _validate_url(
            values,
            "AIRFLOW_DATABASE_URL",
            schemes={"postgresql", "postgresql+psycopg2"},
            host="postgres",
            port=5432,
            database=airflow_db,
            password_key="POSTGRES_PASSWORD",
            username_key="POSTGRES_USER",
        )
    )
    errors.extend(
        _validate_url(
            values,
            "REDIS_URL",
            schemes={"redis"},
            host="redis",
            port=6379,
            database="0",
            password_key="REDIS_PASSWORD",
        )
    )
    errors.extend(
        _validate_url(
            values,
            "AIRFLOW_REDIS_URL",
            schemes={"redis"},
            host="redis",
            port=6379,
            database="1",
            password_key="REDIS_PASSWORD",
        )
    )

    if values.get("NEXT_PUBLIC_API_URL") != "same-origin":
        errors.append("NEXT_PUBLIC_API_URL must be same-origin")
    try:
        production_url = urlparse(values.get("PRODUCTION_BASE_URL", ""))
        production_hostname = production_url.hostname
        production_port = production_url.port
    except ValueError:
        production_url = urlparse("")
        production_hostname = None
        production_port = None
    if (
        production_url.scheme != "https"
        or not production_hostname
        or production_port not in (None, 443)
        or production_url.username is not None
        or production_url.password is not None
        or production_url.path not in ("", "/")
        or production_url.query
        or production_url.fragment
    ):
        errors.append("PRODUCTION_BASE_URL must be an https URL")
    try:
        cors_origins = json.loads(values.get("SECURITY_CORS_ORIGINS", ""))
        if (
            not isinstance(cors_origins, list)
            or not cors_origins
            or not all(isinstance(origin, str) for origin in cors_origins)
        ):
            raise ValueError
        parsed_origins = [urlparse(origin) for origin in cors_origins]
        if not all(
            origin.scheme == "https"
            and origin.hostname
            and origin.port in (None, 443)
            and origin.username is None
            and origin.password is None
            and origin.path in ("", "/")
            and not origin.query
            and not origin.fragment
            for origin in parsed_origins
        ):
            raise ValueError
    except (TypeError, ValueError, json.JSONDecodeError):
        errors.append(
            "SECURITY_CORS_ORIGINS must be a non-empty JSON list of https origins"
        )
    for key in ("NEXT_PUBLIC_WS_URL", "NEXT_PUBLIC_MARKET_WS_URL"):
        if values.get(key) != "same-origin":
            errors.append(f"{key} must be same-origin")

    return errors


def validate_image_manifest(values: dict[str, str]) -> list[str]:
    errors = []
    for key in sorted(REQUIRED_IMAGE_KEYS):
        value = values.get(key, "")
        if not value:
            errors.append(f"{key} is required")
        elif not IMMUTABLE_IMAGE_PATTERN.fullmatch(value):
            errors.append(f"{key} must be pinned with @sha256:<64 hex characters>")
    return errors


def main() -> int:
    get_key: str | None = None
    validate_images = len(sys.argv) >= 2 and sys.argv[1] == "--images"
    if validate_images:
        path = Path(sys.argv[2] if len(sys.argv) > 2 else ".env.images")
    elif len(sys.argv) >= 3 and sys.argv[1] == "--get":
        get_key = sys.argv[2]
        path = Path(sys.argv[3] if len(sys.argv) > 3 else ".env.production")
    else:
        path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env.production")
    if not path.is_file():
        print(f"Production environment file not found: {path}", file=sys.stderr)
        return 1
    try:
        values = parse_env_file(path)
    except (OSError, ValueError) as exc:
        print(f"Invalid production environment file: {exc}", file=sys.stderr)
        return 1

    if get_key is not None:
        value = values.get(get_key)
        if value is None:
            print(f"Production environment key not found: {get_key}", file=sys.stderr)
            return 1
        print(value)
        return 0

    errors = validate_image_manifest(values) if validate_images else validate(values)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if validate_images:
        print("Production image manifest is valid and immutable.")
    else:
        print("Production environment contract is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
