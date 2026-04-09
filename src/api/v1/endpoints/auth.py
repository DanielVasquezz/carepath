# src/api/v1/endpoints/auth.py
"""
CarePath — Authentication Endpoints
=====================================
Handles login and token operations.

POST /auth/login  → authenticate and receive JWT token
POST /auth/logout → invalidate token (client-side)

Why OAuth2 password flow?
Because it's the standard that every HTTP client,
browser, and mobile app already knows how to use.
FastAPI's OAuth2PasswordRequestForm handles the
username/password parsing automatically.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import create_access_token, verify_password
from src.models.db.patient_db import PatientDB

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


class Token(BaseModel):
    """
    OAuth2 token response schema.
    Standard format defined by OAuth2 specification.
    Every OAuth2 client expects exactly these fields.
    """
    access_token: str
    token_type: str = "bearer"
    # token_type is always "bearer" for JWT
    # "bearer" means "whoever bears this token has access"


class TokenData(BaseModel):
    """Data extracted from a decoded JWT token."""
    user_id: str
    role: str


@router.post(
    "/login",
    response_model=Token,
    summary="Login and receive JWT token",
    description="""
    Authenticates a user with email and password.
    Returns a JWT access token valid for 30 minutes.
    
    Include the token in subsequent requests:
    `Authorization: Bearer <token>`
    
    Uses OAuth2 password flow — send credentials
    as form data, not JSON.
    """,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    POST /api/v1/auth/login
    
    OAuth2PasswordRequestForm automatically parses:
      - username (we use email as username)
      - password
    
    Sent as form data (application/x-www-form-urlencoded)
    not JSON — this is the OAuth2 standard.
    """
    # Find user by email
    # OAuth2 uses 'username' field — we treat it as email
    result = await db.execute(
        select(PatientDB).where(
            PatientDB.email == form_data.username,
            PatientDB.is_active == True,  # noqa: E712
        )
    )
    user = result.scalar_one_or_none()

    # Verify credentials
    # We check both conditions together and return the same
    # error message for both cases — this is intentional.
    # Separate messages ("user not found" vs "wrong password")
    # help attackers enumerate valid usernames. Same message
    # for both cases prevents this (user enumeration attack).
    if user is None or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    access_token = create_access_token(
        subject=user.id,
        role=user.role,
    )

    return Token(access_token=access_token)