# src/api/deps.py
"""
CarePath — FastAPI Dependencies
================================
Reusable dependencies injected into endpoints via Depends().

The dependency injection pattern means:
  - Security logic is written once, used everywhere
  - Endpoints declare what they need, not how to get it
  - Testing is easy — swap real dependencies for mocks

Dependency chain for a protected endpoint:
    Request arrives with Authorization: Bearer <token>
         ↓
    get_current_user() extracts and validates token
         ↓
    Returns authenticated PatientDB or DoctorDB object
         ↓
    Endpoint receives the verified user, does its work
"""
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import decode_access_token
from src.models.db.patient_db import PatientDB
from src.models.enums import UserRole

# OAuth2PasswordBearer tells FastAPI:
# "this API uses OAuth2 with password flow"
# "tokens come in the Authorization: Bearer <token> header"
# "if no token → redirect to /api/v1/auth/login"
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> PatientDB:
    """
    Core security dependency.
    
    Extracts the JWT from the Authorization header,
    verifies it, and returns the authenticated user
    from the database.
    
    Used by: all protected endpoints
    
    Raises 401 if:
      - No token provided
      - Token is expired
      - Token signature is invalid
      - User no longer exists in DB
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
        # WWW-Authenticate header is required by OAuth2 spec
        # It tells clients how to authenticate
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    # Verify user still exists and is active
    result = await db.execute(
        select(PatientDB).where(
            PatientDB.id == user_id,
            PatientDB.is_active == True,  # noqa: E712
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_patient(
    current_user: PatientDB = Depends(get_current_user),
) -> PatientDB:
    """
    Ensures the authenticated user has PATIENT role.
    
    Dependency chain:
        get_current_user() → get_current_active_patient()
    
    Raises 403 if the user is not a patient.
    403 Forbidden = authenticated but not authorized.
    401 Unauthorized = not authenticated at all.
    The distinction matters for security auditing.
    """
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to patients",
        )
    return current_user


async def get_current_doctor(
    current_user: PatientDB = Depends(get_current_user),
) -> PatientDB:
    """
    Ensures the authenticated user has DOCTOR role.
    Raises 403 if the user is not a doctor.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to medical staff",
        )
    return current_user


async def get_current_admin(
    current_user: PatientDB = Depends(get_current_user),
) -> PatientDB:
    """
    Ensures the authenticated user has ADMIN role.
    Raises 403 if the user is not an admin.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators",
        )
    return current_user