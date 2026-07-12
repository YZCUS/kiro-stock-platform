import os
from pathlib import Path

TEST_ARTIFACT_ROOT = Path("/tmp/kiro-qlib-tests")
os.environ.setdefault("QLIB_ARTIFACT_ROOT", str(TEST_ARTIFACT_ROOT))
os.environ.setdefault("QLIB_PROVIDER_URI", str(TEST_ARTIFACT_ROOT / "provider"))
