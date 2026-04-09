"""
CarePath — Patient Endpoints
==============================
HTTP routes for patient management.
All routes use PostgreSQL via SQLAlchemy async.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.db.patient_db import PatientDB
from src.models.patient import Patient, PatientCreate
from src.core.security import hash_password
# CORRECCIÓN AQUÍ: Importamos desde deps, no desde security
from src.api.deps import get_current_user

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
)


@router.post(
    "/",
    response_model=Patient,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
    description="""
    Creates a new patient account in CarePath.
    Returns the created patient without the password field.
    Raises 400 if the email is already registered.
    """,
)
async def create_patient(
    patient_data: PatientCreate,
    db: AsyncSession = Depends(get_db),
) -> Patient:
    # Check duplicate email
    result = await db.execute(
        select(PatientDB).where(PatientDB.email == patient_data.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {patient_data.email} is already registered",
        )

    # Create DB row
    db_patient = PatientDB(
        first_name=patient_data.first_name,
        last_name=patient_data.last_name,
        email=patient_data.email,
        date_of_birth=patient_data.date_of_birth,
        phone=patient_data.phone,
        hashed_password=hash_password(patient_data.password),  # bcrypt now
    )
    
    db.add(db_patient)
    await db.flush()
    # AGREGADO: Necesario para guardar en PostgreSQL realmente
    await db.commit()
    await db.refresh(db_patient)

    return Patient(
        id=db_patient.id,
        first_name=db_patient.first_name,
        last_name=db_patient.last_name,
        email=db_patient.email,
        date_of_birth=db_patient.date_of_birth,
        phone=db_patient.phone,
    )


# En src/api/v1/endpoints/patients.py

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_user),
) -> Patient:

    if current_user.role == UserRole.PATIENT and current_user.id != patient_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver otros perfiles")
    
    result = await db.execute(
        select(PatientDB).where(
            PatientDB.id == patient_id,
            PatientDB.is_active == True,  # noqa: E712
        )
    )
    db_patient = result.scalar_one_or_none()

    if db_patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )

    return Patient(
        id=db_patient.id,
        first_name=db_patient.first_name,
        last_name=db_patient.last_name,
        email=db_patient.email,
        date_of_birth=db_patient.date_of_birth,
        phone=db_patient.phone,
    )


@router.get(
    "/",
    response_model=list[Patient],
    summary="List all active patients",
)
async def list_patients(
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_user),  
) -> list[Patient]:
    result = await db.execute(
        select(PatientDB)
        .where(PatientDB.is_active == True)
        .order_by(PatientDB.created_at.desc())
    )
    db_patients = result.scalars().all()

    return [
        Patient(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            email=p.email,
            date_of_birth=p.date_of_birth,
            phone=p.phone,
        )
        for p in db_patients
    ]