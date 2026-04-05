# src/api/v1/endpoints/patients.py
"""
CarePath — Patient Endpoints
==============================
HTTP routes for patient management.

All routes follow REST conventions:
  POST   /patients       → create a new patient
  GET    /patients/{id}  → get a specific patient
  GET    /patients       → list patients (doctors/admins only)

Why no PUT /patients/{id} (update)?
Updates are handled through specific sub-resources.
A patient changes their email → POST /patients/{id}/email
This is intentional: it makes audit logging easier and
prevents accidental mass-updates.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.models.patient import Patient, PatientCreate


router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)

# Temporary in-memory store — replaced by PostgreSQL in Lesson 4
# This lets us build and test the API without a database
_patients_db: dict[UUID, Patient] = {}

@router.post(
    "/",
    response_model=Patient,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
    description="""
    Creates a new patient account in the system.
    
    The password is hashed before storage (bcrypt).
    Returns the created patient without the password field.
    
    Raises 400 if the email is already registered.
    """,
)

async def create_patient(patient_data: PatientCreate) -> Patient:
    """
    POST /api/v1/patients
    
    FastAPI automatically:
    - Validates patient_data using PatientCreate validators
    - Returns 422 if validation fails (wrong email, short password, etc.)
    - Serializes the response using the Patient model
    - Documents this endpoint in /docs
    """
    
    for existing in _patients_db.values():
        if existing.email == patient_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {patient_data.email} already registered",
            )
    
    # Create patient from registration data
    # In production: hash the password here with bcrypt
    
    new_patient = Patient(
        first_name=patient_data.first_name,
        last_name=patient_data.last_name,
        email=patient_data.email,
        date_of_birth=patient_data.date_of_birth,
        phone=patient_data.phone,
    )
    
    # Store in our temporary DB
    _patients_db[new_patient.id] = new_patient

    return new_patient

@router.get(
    "/{patient_id}",
    response_model=Patient,
    summary="Get patient by ID",
)
async def get_patient(patient_id: UUID) -> Patient:
    """
    GET /api/v1/patients/{patient_id}
    
    FastAPI automatically:
    - Converts the {patient_id} path parameter to UUID type
    - Returns 422 if patient_id is not a valid UUID format
    """
    patient = _patients_db.get(patient_id)
    
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )
    
    return patient

@router.get(
    "/",
    response_model=list[Patient],
    summary="List all patients",
)
async def list_patients() -> list[Patient]:
    """
    GET /api/v1/patients
    
    In production: restricted to doctors and admins.
    Patients can only see their own record.
    Authorization added in Lesson 4 — Security.
    """
    return list(_patients_db.values())
    