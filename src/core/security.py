# src/core/security.py
"""
CarePath — Security Engine
===========================
Handles all cryptographic operations:
  - Password hashing with native bcrypt
  - JWT token creation and verification
  - User extraction from tokens

Why centralize security here?
Because security logic scattered across files is how
vulnerabilities are introduced. One file, one place
to audit, one place to update if an algorithm changes.

OWASP compliance:
  A02 — Cryptographic Failures: bcrypt with cost factor 12
  A07 — Identification and Authentication Failures: JWT with expiry
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import jwt, JWTError

from src.core.config import settings


# ── Password Hashing (Native Bcrypt) ──────────────────────────────
def hash_password(plain_password: str) -> str:
    """
    Converts plain text password to bcrypt hash using native bcrypt.

    Example:
        "securepass123" → "$2b$12$...."

    One-way function: irreversible.
    """
    pwd_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against its stored bcrypt hash.

    Uses timing-safe comparison internally via bcrypt.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT Token Operations ──────────────────────────────────────────
def create_access_token(
    subject: UUID | str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a signed JWT access token.

    Payload includes:
        sub  → user ID (UUID as string)
        role → user role for RBAC
        exp  → expiration time
        iat  → issued at time
    """
    now = datetime.now(timezone.utc)

    expire = now + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and verifies JWT token.

    Raises:
        JWTError: if token is invalid, expired, or tampered.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as e:
        raise e