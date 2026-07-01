"""SQLite-backed user database with bcrypt password/PIN hashing."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any

import bcrypt

from auto_cell.auth.models import Role, UserCreate, UserInDB


def _hash_secret(secret: str) -> str:
    """Hash a password or PIN with bcrypt."""
    encoded = secret.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("secret exceeds bcrypt maximum length of 72 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def _verify_secret(secret: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            secret.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except ValueError:
        return False


class UserDB:
    """Minimal user database for GMP identity management.

    Passwords and PINs are hashed with bcrypt. PINs are used as part of the
    electronic signature on approval/reject decisions.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    pin_hash TEXT NOT NULL,
                    disabled INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def _row_to_user(self, row: sqlite3.Row) -> UserInDB:
        return UserInDB(
            user_id=row["user_id"],
            username=row["username"],
            full_name=row["full_name"],
            role=Role(row["role"]),
            disabled=bool(row["disabled"]),
            password_hash=row["password_hash"],
            pin_hash=row["pin_hash"],
        )

    def create_user(self, user: UserCreate, user_id: str | None = None) -> UserInDB:
        new_id = user_id or str(uuid.uuid4())
        password_hash = _hash_secret(user.password)
        pin_hash = _hash_secret(user.pin)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, full_name, role, password_hash, pin_hash, disabled)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    new_id,
                    user.username,
                    user.full_name,
                    user.role.value,
                    password_hash,
                    pin_hash,
                ),
            )
            conn.commit()
        result = self.get_user_by_id(new_id)
        if result is None:
            raise RuntimeError("failed to create user")
        return result

    def get_user_by_username(self, username: str) -> UserInDB | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_user(row)

    def get_user_by_id(self, user_id: str) -> UserInDB | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                return None
            return self._row_to_user(row)

    def list_users(self) -> list[UserInDB]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
            return [self._row_to_user(row) for row in rows]

    def verify_password(self, plain_password: str, user: UserInDB) -> bool:
        return _verify_secret(plain_password, user.password_hash)

    def verify_pin(self, plain_pin: str, user: UserInDB) -> bool:
        return _verify_secret(plain_pin, user.pin_hash)

    def authenticate(self, username: str, password: str) -> UserInDB | None:
        user = self.get_user_by_username(username)
        if user is None or user.disabled:
            return None
        if not self.verify_password(password, user):
            return None
        return user

    def update_user(self, user_id: str, **kwargs: Any) -> UserInDB | None:
        """Update selected fields. Password/PIN updates are re-hashed if provided."""
        allowed = {"username", "full_name", "role", "disabled"}
        set_clauses: list[str] = []
        values: list[Any] = []
        for key, value in kwargs.items():
            if key == "password":
                set_clauses.append("password_hash = ?")
                values.append(_hash_secret(value))
            elif key == "pin":
                set_clauses.append("pin_hash = ?")
                values.append(_hash_secret(value))
            elif key in allowed:
                set_clauses.append(f"{key} = ?")
                values.append(value.value if isinstance(value, Role) else value)
            else:
                raise ValueError(f"unknown field: {key}")
        if not set_clauses:
            return self.get_user_by_id(user_id)
        values.append(user_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(set_clauses)} WHERE user_id = ?",
                values,
            )
            conn.commit()
        return self.get_user_by_id(user_id)
