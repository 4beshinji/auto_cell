"""JWT token creation/validation and dependency helpers."""

from __future__ import annotations

import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from auto_cell.auth.db import UserDB
from auto_cell.auth.models import Role, TokenData, UserInDB

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("HMI_JWT_EXPIRE_MINUTES", "60"))

_SECRET_KEY: str | None = os.getenv("HMI_JWT_SECRET")
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_urlsafe(32)
    warnings.warn(
        "HMI_JWT_SECRET is not set; using an ephemeral secret. Set HMI_JWT_SECRET for persistence across restarts.",
        RuntimeWarning,
        stacklevel=2,
    )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/hmi/auth/token", auto_error=True)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        role_value: str | None = payload.get("role")
        role = Role(role_value) if role_value else None
        if user_id is None:
            return None
        return TokenData(user_id=user_id, role=role)
    except (JWTError, ValueError):
        return None


def get_current_user(token: str, user_db: UserDB) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    user = user_db.get_user_by_id(token_data.user_id)
    if user is None or user.disabled:
        raise credentials_exception
    return user


def require_role(*roles: Role):
    def checker(user: UserInDB = Depends(lambda: None)) -> UserInDB:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient privileges",
            )
        return user
    return checker
