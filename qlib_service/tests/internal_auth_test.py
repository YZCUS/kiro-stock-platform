from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.main import require_internal_token


def test_qlib_internal_auth_accepts_configured_secret():
    settings = SimpleNamespace(environment="production", internal_token="qlib-secret")

    require_internal_token("qlib-secret", settings)


def test_qlib_internal_auth_rejects_development_default_in_production():
    settings = SimpleNamespace(
        environment="production", internal_token="dev-qlib-token"
    )

    with pytest.raises(HTTPException) as exc_info:
        require_internal_token("dev-qlib-token", settings)

    assert exc_info.value.status_code == 503
