"""Authentication dependency for service-to-service backend endpoints."""

from secrets import compare_digest

from fastapi import Depends, Header, HTTPException, status

from app.settings import Settings, get_settings
from core.auth_dependencies import get_optional_current_user


def require_internal_token(
    x_internal_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require the dedicated backend token and fail closed in production."""

    expected = settings.INTERNAL_API_TOKEN
    if not expected:
        if settings.app.environment.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="internal API token is not configured",
            )
        expected = "dev-internal-token"

    if not x_internal_token or not compare_digest(x_internal_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid internal token",
        )


def require_active_user_or_internal_token(
    x_internal_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    current_user=Depends(get_optional_current_user),
) -> None:
    """Allow an authenticated UI user or a trusted internal caller."""

    if current_user is not None:
        return
    require_internal_token(x_internal_token=x_internal_token, settings=settings)
