from uuid import UUID
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db 
from src.core.security import decode_access_token
from src.models.db.patient_db import PatientDB
from src.models.enums import UserRole
from src.core.config import settings

# CORRECCIÓN: Usamos la ruta completa que Swagger espera ver.
# Si tu prefijo es /api/v1, asegúrate de que coincida aquí.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login"
)

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> PatientDB:
    """
    Valida el token JWT y retorna el usuario actual de la base de datos.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Decodificar el token
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # 2. Validar que sea un UUID válido
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise credentials_exception
            
    except (JWTError, Exception):
        raise credentials_exception
    
    # 3. Buscar en la base de datos
    # Usamos scalar_one_or_none para evitar errores si no existe
    result = await db.execute(
        select(PatientDB).where(
            PatientDB.id == user_uuid, 
            PatientDB.is_active == True
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_patient(
    current_user: PatientDB = Depends(get_current_user)
) -> PatientDB:
    """Valida que el usuario sea un paciente."""
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access restricted to patients"
        )
    return current_user

async def get_current_doctor(
    current_user: PatientDB = Depends(get_current_user)
) -> PatientDB:
    """Valida que el usuario sea un doctor."""
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access restricted to doctors"
        )
    return current_user

async def get_current_admin(
    current_user: PatientDB = Depends(get_current_user)
) -> PatientDB:
    """Valida que el usuario sea un administrador."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access restricted to admins"
        )
    return current_user