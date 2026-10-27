"""Pytest test fixtures."""
import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure backend package is in pythonpath
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.db import init_db
from app.main import create_app

@pytest.fixture(scope="session")
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        settings.RW_ARTIFACTS_DIR = str(tmp_path / "artifacts")
        settings.RW_DB_PATH = str(tmp_path / "artifacts" / "test.sqlite3")
        init_db(settings.db_path)
        yield tmp_path

@pytest.fixture
def client(temp_workspace):
    from fastapi.testclient import TestClient
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
