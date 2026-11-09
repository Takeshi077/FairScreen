from __future__ import annotations

import contextlib
import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parents[2] / "data" / "test_fairscreen.db"
for stale in (TEST_DB, Path(str(TEST_DB) + "-wal"), Path(str(TEST_DB) + "-shm")):
    with contextlib.suppress(FileNotFoundError):
        stale.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["FAIRSCREEN_ENV"] = "test"
os.environ["FAIRSCREEN_BOOTSTRAP"] = "400"
os.environ["FAIRSCREEN_PERMUTATION"] = "400"
os.environ["LLM_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    init_db()


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client(clean_db):
    with TestClient(app) as test_client:
        yield test_client
