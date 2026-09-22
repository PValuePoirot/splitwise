"""Password hashing and JWT token utilities."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Argon2 is the winner of the 2015 Password Hashing Competition.
# We disable bcrypt/argon2 warnings from passlib's version detection.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
    subject: str | int,
    expires_delta: timedelta,
    secret: str,
    token_type: str,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        secret=settings.jwt_secret,
        token_type="access",
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        secret=settings.jwt_refresh_secret,
        token_type="refresh",
    )


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on invalid/expired tokens."""
    return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])


def decode_access_token(token: str) -> int:
    payload = decode_token(token, settings.jwt_secret)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return int(payload["sub"])


def decode_refresh_token(token: str) -> int:
    payload = decode_token(token, settings.jwt_refresh_secret)
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return int(payload["sub"])
