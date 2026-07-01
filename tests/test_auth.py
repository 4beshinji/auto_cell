"""Authentication and authorization tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, UserCreate
from auto_cell.auth.security import create_access_token, decode_access_token
from auto_cell.hmi.approval_api import Services, app


@pytest.fixture
def user_db(tmp_path: Path):
    return UserDB(tmp_path / "auth" / "users.db")


def test_password_and_pin_hashing(user_db):
    user = user_db.create_user(
        UserCreate(
            username="alice",
            full_name="Alice Smith",
            password="super-secret-12",
            pin="4242",
            role=Role.OPERATOR,
        )
    )
    assert user.password_hash != "super-secret-12"
    assert user.pin_hash != "4242"
    assert user_db.verify_password("super-secret-12", user)
    assert user_db.verify_pin("4242", user)
    assert not user_db.verify_password("wrong", user)
    assert not user_db.verify_pin("0000", user)


def test_authenticate(user_db):
    user_db.create_user(
        UserCreate(
            username="bob",
            full_name="Bob Jones",
            password="password123",
            pin="1111",
            role=Role.REVIEWER,
        )
    )
    assert user_db.authenticate("bob", "password123") is not None
    assert user_db.authenticate("bob", "wrong") is None
    assert user_db.authenticate("unknown", "password123") is None


def test_disabled_user_cannot_authenticate(user_db):
    user = user_db.create_user(
        UserCreate(
            username="carol",
            full_name="Carol White",
            password="password123",
            pin="2222",
            role=Role.OPERATOR,
        )
    )
    user_db.update_user(user.user_id, disabled=True)
    assert user_db.authenticate("carol", "password123") is None


def test_create_access_token_roundtrip(user_db):
    user = user_db.create_user(
        UserCreate(
            username="dave",
            full_name="Dave Brown",
            password="password123",
            pin="3333",
            role=Role.QA,
        )
    )
    token = create_access_token({"sub": user.user_id, "role": user.role.value})
    data = decode_access_token(token)
    assert data is not None
    assert data.user_id == user.user_id
    assert data.role == Role.QA


def test_login_endpoint(tmp_path: Path, monkeypatch):
    user_db = UserDB(tmp_path / "auth" / "users.db")
    user_db.create_user(
        UserCreate(
            username="loginuser",
            full_name="Login User",
            password="password123",
            pin="1234",
            role=Role.OPERATOR,
        )
    )
    services = Services.__new__(Services)
    services.user_db = user_db
    monkeypatch.setattr("auto_cell.hmi.approval_api._services", services)

    with TestClient(app) as c:
        resp = c.post(
            "/hmi/auth/token",
            data={"username": "loginuser", "password": "password123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        resp = c.post(
            "/hmi/auth/token",
            data={"username": "loginuser", "password": "wrong"},
        )
        assert resp.status_code == 401
