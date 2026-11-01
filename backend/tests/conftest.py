"""Pytest test fixtures."""

import sys
import tempfile
from pathlib import Path
import pytest

# Ensure backend package is in pythonpath
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        settings.RW_ARTIFACTS_DIR = str(tmp_path / "artifacts")
        settings.RW_DB_PATH = str(tmp_path / "artifacts" / "test.sqlite3")
        # Test isolation: NEVER touch live providers. Force offline mode and
        # blank credentials for the whole test session, regardless of the
        # developer's local .env (which may contain real keys).
        settings.RW_AI_MODE = "offline"
        settings.RW_META_API_KEY = ""
        settings.RW_META_BASE_URL = ""
        settings.RW_META_MODEL = ""
        init_db(settings.db_path)
        yield tmp_path


@pytest.fixture
def client(temp_workspace):
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
