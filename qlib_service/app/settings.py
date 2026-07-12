from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        "postgresql://postgres:postgres@postgres:5432/stock_analysis",
        alias="DATABASE_URL",
    )
    internal_token: str = Field("dev-qlib-token", alias="QLIB_INTERNAL_TOKEN")
    environment: str = Field("development", alias="QLIB_ENVIRONMENT")
    artifact_root: Path = Field(Path("/app/artifacts"), alias="QLIB_ARTIFACT_ROOT")
    provider_uri: Path = Field(
        Path("/app/artifacts/provider"), alias="QLIB_PROVIDER_URI"
    )
    default_market: str = Field("US", alias="QLIB_DEFAULT_MARKET")
    default_universe: str = Field("active_us", alias="QLIB_DEFAULT_UNIVERSE")
    default_model_name: str = Field(
        "lightgbm_alpha158", alias="QLIB_DEFAULT_MODEL_NAME"
    )
    default_feature_set: str = Field("alpha158", alias="QLIB_DEFAULT_FEATURE_SET")
    max_universe_size: int = Field(500, alias="QLIB_MAX_UNIVERSE_SIZE")
    cpu_threads: int = Field(2, alias="QLIB_CPU_THREADS", ge=1, le=64)
    stale_job_seconds: int = Field(
        7200, alias="QLIB_STALE_JOB_SECONDS", ge=60, le=86400
    )
    database_pool_size: int = Field(2, alias="QLIB_DATABASE_POOL_SIZE", ge=1, le=20)
    database_max_overflow: int = Field(
        1, alias="QLIB_DATABASE_MAX_OVERFLOW", ge=0, le=20
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    settings.provider_uri.mkdir(parents=True, exist_ok=True)
    return settings
