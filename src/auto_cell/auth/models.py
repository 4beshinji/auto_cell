"""User, role, and token models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    QA = "qa"
    ADMIN = "admin"


class User(BaseModel):
    """Public user information returned by the API."""

    user_id: str
    username: str
    full_name: str
    role: Role
    disabled: bool = False


class UserInDB(User):
    """User with credential hashes stored in the database."""

    password_hash: str
    pin_hash: str


class UserCreate(BaseModel):
    """Payload for creating a new user."""

    username: str = Field(..., min_length=1, max_length=64)
    full_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=8)
    pin: str = Field(..., min_length=4, max_length=64)
    role: Role


class Token(BaseModel):
    """OAuth2 access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT payload."""

    user_id: str | None = None
    role: Role | None = None
