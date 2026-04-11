from typing import List
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import create_access_token, verify_password, hash_password
from src.models.db.patient_db import PatientDB
from src.api.deps import get_current_user   # ✅ FIX: protección endpoint

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["authentication"])

# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    date_of_birth: date   # ✅ requerido por DB


# ─────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Verificar si el usuario ya existe
        result = await db.execute(
            select(PatientDB).where(PatientDB.email == user_in.email)
        )

        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # 2. Crear usuario
        new_user = PatientDB(
            email=user_in.email,
            hashed_password=hash_password(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            date_of_birth=user_in.date_of_birth,
            is_active=True,
            role="patient"
        )

        # 3. Guardar en DB
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {
            "message": "User created successfully",
            "id": str(new_user.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:

    logger.info(f"Login attempt: {form_data.username}")

    try:
        # 1. Buscar usuario
        result = await db.execute(
            select(PatientDB).where(PatientDB.email == form_data.username)
        )

        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Verificar password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Crear token
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
        )

        return Token(
            access_token=access_token,
            token_type="bearer"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login system error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


# ─────────────────────────────────────────────
# USERS LIST (PROTEGIDO 🔐)
# ─────────────────────────────────────────────
@router.get("/users/list")
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_user)  # 🔐 PROTEGIDO
):
    try:
        logger.info(f"User list accessed by: {current_user.email}")

        result = await db.execute(select(PatientDB))
        users = result.scalars().all()

        return [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": f"{u.first_name} {u.last_name}",
                "date_of_birth": u.date_of_birth,
                "role": u.role,
                "is_active": u.is_active,
            }
            for u in users
        ]

    except Exception as e:
        logger.error(f"Error fetching users list: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving users"
        )