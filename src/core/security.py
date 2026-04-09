# src/core/security.py
"""
CarePath — Security Engine
===========================
Handles all cryptographic operations:
  - Password hashing with bcrypt
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
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

# ── Password Hashing ──────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    # rounds=12 means 2^12 = 4096 iterations
    # Each iteration makes brute force slower
    # 12 is the industry standard balance between
    # security and performance (~250ms per hash)
    # Never go below 10. Never need to go above 14.
)


def hash_password(plain_password: str) -> str:
    """
    Converts plain text password to bcrypt hash.
    
    "securepass123" → "$2b$12$LQv3c1yqBWVHxkd0LHAkCO..."
    
    This is a one-way operation — you cannot reverse it.
    Store only the hash. Never the plain text.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against its stored hash.
    
    How it works:
    1. Extracts the salt and cost factor from the stored hash
    2. Re-hashes the plain password with those parameters
    3. Compares the result with the stored hash
    
    Returns True if they match, False otherwise.
    The comparison is timing-safe — prevents timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Operations ──────────────────────────────────────────
def create_access_token(
    subject: UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a signed JWT access token.
    
    The token contains:
      sub  → subject (patient/doctor UUID) — standard JWT claim
      role → UserRole value for RBAC
      exp  → expiration timestamp — standard JWT claim
      iat  → issued at timestamp — standard JWT claim
    
    Why include role in the token?
    So the server can enforce RBAC without a DB lookup
    on every request. The role is cryptographically
    bound to the user ID — it cannot be tampered with.
    
    Args:
        subject: UUID of the authenticated user
        role: UserRole value (patient, doctor, admin)
        expires_delta: custom expiration, defaults to settings value
    
    Returns:
        Signed JWT string
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),      # always string in JWT
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
    Decodes and verifies a JWT token.
    
    Verification includes:
      - Signature validity (was it signed with our SECRET_KEY?)
      - Expiration check (has the token expired?)
      - Claims validation (does it have required fields?)
    
    Raises JWTError if any check fails.
    The caller (get_current_user) handles the exception.
    
    Returns:
        Decoded payload dict with sub, role, exp, iat
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )