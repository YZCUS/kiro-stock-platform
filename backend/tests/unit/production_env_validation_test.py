import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "validate-production-env.py"
)
SPEC = importlib.util.spec_from_file_location("validate_production_env", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _valid_values() -> dict[str, str]:
    password = "a/b@c:password-with-symbols"
    encoded = "a%2Fb%40c%3Apassword-with-symbols"
    return {
        "POSTGRES_DB": "stock_analysis",
        "POSTGRES_USER": "stock_admin",
        "POSTGRES_PASSWORD": password,
        "APP_ENVIRONMENT": "production",
        "APP_DEBUG": "false",
        "DATABASE_URL": f"postgresql://stock_admin:{encoded}@postgres:5432/stock_analysis",
        "REDIS_PASSWORD": password,
        "REDIS_URL": f"redis://:{encoded}@redis:6379/0",
        "SECURITY_SECRET_KEY": "s" * 32,
        "SECURITY_CORS_ORIGINS": '["https://stocks.example.com"]',
        "INTERNAL_API_TOKEN": "i" * 32,
        "AIRFLOW_FERNET_KEY": "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
        "AIRFLOW_SECRET_KEY": "a" * 32,
        "AIRFLOW_DATABASE_URL": f"postgresql+psycopg2://stock_admin:{encoded}@postgres:5432/airflow",
        "AIRFLOW_REDIS_URL": f"redis://:{encoded}@redis:6379/1",
        "AIRFLOW_ADMIN_PASSWORD": "p" * 32,
        "QLIB_INTERNAL_TOKEN": "q" * 32,
        "NEXT_PUBLIC_API_URL": "same-origin",
        "PRODUCTION_BASE_URL": "https://stocks.example.com",
        "NEXT_PUBLIC_WS_URL": "same-origin",
        "NEXT_PUBLIC_MARKET_WS_URL": "same-origin",
    }


def test_production_environment_accepts_url_encoded_passwords():
    assert MODULE.validate(_valid_values()) == []


def test_production_environment_rejects_placeholder_and_wrong_database_host():
    values = _valid_values()
    values["INTERNAL_API_TOKEN"] = "CHANGE_THIS_INTERNAL_API_TOKEN"
    values["DATABASE_URL"] = values["DATABASE_URL"].replace("@postgres", "@localhost")

    errors = MODULE.validate(values)

    assert "INTERNAL_API_TOKEN still contains a placeholder" in errors
    assert "DATABASE_URL must use Docker host postgres" in errors


def test_production_environment_rejects_mismatched_connection_identity():
    values = _valid_values()
    values["DATABASE_URL"] = values["DATABASE_URL"].replace(
        "stock_admin:", "wrong_user:"
    )
    values["AIRFLOW_REDIS_URL"] = values["AIRFLOW_REDIS_URL"].replace(
        ":6379/1", ":6380/1"
    )

    errors = MODULE.validate(values)

    assert "DATABASE_URL username does not match POSTGRES_USER" in errors
    assert "AIRFLOW_REDIS_URL must use port 6379" in errors


def test_production_environment_rejects_malformed_public_urls():
    values = _valid_values()
    values["PRODUCTION_BASE_URL"] = "https://stocks.example.com:invalid/path"
    values["SECURITY_CORS_ORIGINS"] = '["https:///missing-host"]'
    values["NEXT_PUBLIC_MARKET_WS_URL"] = "wss://stocks.example.com/ws"

    errors = MODULE.validate(values)

    assert "PRODUCTION_BASE_URL must be an https URL" in errors
    assert (
        "SECURITY_CORS_ORIGINS must be a non-empty JSON list of https origins" in errors
    )
    assert "NEXT_PUBLIC_MARKET_WS_URL must be same-origin" in errors


def test_production_environment_rejects_noncanonical_fernet_key():
    values = _valid_values()
    values["AIRFLOW_FERNET_KEY"] = f"!!{values['AIRFLOW_FERNET_KEY']}"

    assert "AIRFLOW_FERNET_KEY must encode exactly 32 bytes" in MODULE.validate(values)


def test_production_image_manifest_requires_all_digest_pins():
    digest = "0" * 64
    images = {
        "BACKEND_IMAGE": f"registry.example/backend@sha256:{digest}",
        "FRONTEND_IMAGE": f"registry.example/frontend@sha256:{digest}",
        "AIRFLOW_IMAGE": f"registry.example/airflow@sha256:{digest}",
        "QLIB_IMAGE": f"registry.example/qlib@sha256:{digest}",
    }

    assert MODULE.validate_image_manifest(images) == []

    images.pop("AIRFLOW_IMAGE")
    images["BACKEND_IMAGE"] = "registry.example/backend:main"
    errors = MODULE.validate_image_manifest(images)

    assert "AIRFLOW_IMAGE is required" in errors
    assert "BACKEND_IMAGE must be pinned with @sha256:<64 hex characters>" in errors
