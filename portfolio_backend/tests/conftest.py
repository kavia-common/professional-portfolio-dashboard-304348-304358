from __future__ import annotations

import os
import uuid
from typing import Dict, Generator, Tuple

# IMPORTANT:
# src.api.core.config.Settings reads `.env` by default; the container's `.env` may contain
# ALLOWED_ORIGINS in a non-JSON format which causes parsing errors at import time.
# Since we must not modify non-test source files, we force test-safe env vars *before*
# importing any `src.api.*` modules.
os.environ.setdefault("ALLOWED_ORIGINS", '["http://testserver"]')
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
# Provide a value so Settings.resolve_database_url doesn't try to read db_connection.txt
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.core.db import get_db
from src.api.core.models import Base, User, UserRole
from src.api.main import app


@pytest.fixture()
def db_engine():
    """
    Provide a per-test in-memory SQLite engine.

    StaticPool is used to keep the same in-memory DB across connections within the test.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session bound to the in-memory test DB."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient with get_db dependency overridden to use the in-memory DB.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _unique_email() -> str:
    return f"u_{uuid.uuid4().hex[:10]}@example.com"


def _unique_username() -> str:
    return f"user_{uuid.uuid4().hex[:10]}"


# PUBLIC_INTERFACE
def register_user(client: TestClient, *, email: str, username: str, password: str) -> Dict:
    """Register a user via the real API."""
    resp = client.post("/auth/register", json={"email": email, "username": username, "password": password})
    return {"status": resp.status_code, "json": resp.json() if resp.content else None, "raw": resp}


# PUBLIC_INTERFACE
def login_user(client: TestClient, *, username: str, password: str) -> Tuple[int, Dict]:
    """Login via the real API and return (status_code, json)."""
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.status_code, resp.json() if resp.content else {}


# PUBLIC_INTERFACE
def auth_headers(token: str) -> Dict[str, str]:
    """Return Authorization headers for a Bearer token."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_credentials() -> Dict[str, str]:
    """Sample user credentials (unique per test)."""
    return {"email": _unique_email(), "username": _unique_username(), "password": "password123"}


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    """
    Create an admin user directly in DB for RBAC testing.
    Login still happens via API to obtain JWT.
    """
    from src.api.core.security import hash_password

    u = User(
        email=_unique_email(),
        username=_unique_username(),
        password_hash=hash_password("adminpass123"),
        role=UserRole.admin,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u
