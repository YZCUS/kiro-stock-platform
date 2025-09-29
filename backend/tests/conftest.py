import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env", override=True)

os.environ.setdefault("DATABASE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_APP_NAME", "Test App")
os.environ.setdefault("APP_APP_VERSION", "0.0.0-test")
os.environ.setdefault("APP_APP_DEBUG", "true")
os.environ.setdefault("SECURITY_SECRET_KEY", "test-secret")
