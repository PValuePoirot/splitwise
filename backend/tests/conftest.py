"""Pytest configuration: in-memory SQLite test database and fixtures."""
from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test settings BEFORE importing app modules.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Group, GroupMember, User  # noqa: E402
from app.auth.security import hash_password  # noqa: E402


@pytest.fixture()
def db() -> Generator:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = TestingSessionLocal()

    def override_get_db() -> Generator:
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def user_a(db) -> User:
    user = User(name="Alice", email="alice@example.com", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def user_b(db) -> User:
    user = User(name="Bob", email="bob@example.com", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def user_c(db) -> User:
    user = User(name="Carol", email="carol@example.com", password_hash=hash_password("password123"))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_token(client, user_a) -> str:
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(auth_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def group_with_members(db, user_a, user_b, user_c) -> Group:
    from sqlalchemy.orm import selectinload

    group = Group(name="Trip", currency="USD", created_by=user_a.id)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user_a.id))
    db.add(GroupMember(group_id=group.id, user_id=user_b.id))
    db.add(GroupMember(group_id=group.id, user_id=user_c.id))
    db.commit()
    # Eagerly load members + their user relationships to avoid detached-instance errors.
    db.refresh(group, attribute_names=["members"])
    for m in group.members:
        db.refresh(m, attribute_names=["user"])
    return group
