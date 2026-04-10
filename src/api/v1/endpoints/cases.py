# src/api/v1/endpoints/cases.py
"""
CarePath — Triage Case Endpoints
==================================
All endpoints use SQLAlchemy DB models (TriageCaseDB, SymptomDB)
for persistence and Pydantic models (TriageCase) for responses.

Security:
  - Patients can only access their own cases (IDOR protection)
  - Only doctors can resolve cases (RBAC)
  - JWT required for all endpoints
"""

from src.services.ai_service import (
    generate_symptom_embeddings,
    generate_triage_recommendation,
)

from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_active_patient, get_current_doctor
from src.core.database import get_db
from src.models.db.patient_db import PatientDB
from src.models.db.triage_db import SymptomDB, TriageCaseDB
from src.models.enums import CaseStatus, TriagePriority
from src.models.symptom import Symptom
from src.models.triage import TriageCase, TriageCaseCreate

router = APIRouter(
    prefix="/cases",
    tags=["triage cases"],
)


def db_case_to_pydantic(db_case: TriageCaseDB) -> TriageCase:
    """
    Converts a SQLAlchemy TriageCaseDB object to a Pydantic TriageCase.
    Bridge between DB persistence and API serialization.
    """
    symptoms = [
        Symptom(
            id=s.id,
            case_id=s.case_id,
            description=s.description,
            severity=s.severity,
            duration_hours=s.duration_hours,
            body_location=s.body_location,
            is_worsening=s.is_worsening,
            reported_at=s.reported_at,
        )
        for s in db_case.symptoms
    ]

    return TriageCase(
        id=db_case.id,
        patient_id=db_case.patient_id,
        chief_complaint=db_case.chief_complaint,
        symptoms=symptoms,
        status=db_case.status,
        priority=db_case.priority,
        ai_recommendation=db_case.ai_recommendation,
        attending_doctor_id=db_case.attending_doctor_id,
        opened_at=db_case.opened_at,
        resolved_at=db_case.resolved_at,
    )


@router.post(
    "/",
    response_model=TriageCase,
    status_code=status.HTTP_201_CREATED,
    summary="Open a new triage case",
)
async def create_case(
    case_data: TriageCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    """
    POST /api/v1/cases/
    Crea un caso y genera automáticamente los embeddings de los síntomas.
    """
    # 1. Crear el caso en la base de datos
    db_case = TriageCaseDB(
        patient_id=current_user.id,
        chief_complaint=case_data.chief_complaint,
        status=CaseStatus.OPEN.value,
    )
    db.add(db_case)
    await db.flush()  # Genera db_case.id

    # 2. Crear síntomas vinculados
    db_symptoms = [
        SymptomDB(
            case_id=db_case.id,
            description=s.description,
            severity=s.severity.value,
            duration_hours=s.duration_hours,
            body_location=s.body_location,
            is_worsening=s.is_worsening,
        )
        for s in case_data.symptoms
    ]
    db.add_all(db_symptoms)
    await db.flush() # Necesario para que db_symptoms tengan IDs

    # --- NUEVO: Generar embeddings para búsqueda semántica inmediata ---
    await generate_symptom_embeddings(db_symptoms, db)

    # 3. Confirmar transacción
    await db.commit()

    # 4. Recargar el caso con sus síntomas para la respuesta
    result = await db.execute(
        select(TriageCaseDB)
        .where(TriageCaseDB.id == db_case.id)
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one()

    return db_case_to_pydantic(db_case)


@router.get(
    "/{case_id}",
    response_model=TriageCase,
    summary="Get triage case details",
)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    """
    GET /api/v1/cases/{case_id}
    Acceso restringido: El paciente solo ve sus propios casos.
    """
    result = await db.execute(
        select(TriageCaseDB)
        .where(
            TriageCaseDB.id == case_id,
            TriageCaseDB.patient_id == current_user.id,
        )
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one_or_none()

    if db_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return db_case_to_pydantic(db_case)


@router.post(
    "/{case_id}/evaluate",
    response_model=TriageCase,
    summary="Run START triage algorithm + AI recommendation",
)
async def evaluate_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    result = await db.execute(
        select(TriageCaseDB)
        .where(
            TriageCaseDB.id == case_id,
            TriageCaseDB.patient_id == current_user.id,
        )
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one_or_none()

    if db_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    # MODIFICACIÓN: Permitir re-evaluar si está en 'in_review' pero NO tiene recomendación
    if db_case.status != CaseStatus.OPEN.value and db_case.ai_recommendation is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Case is already {db_case.status} with a recommendation"
        )

    # 1. Asegurar embeddings
    await generate_symptom_embeddings(db_case.symptoms, db)

    # 2. Algoritmo START
    pydantic_case = db_case_to_pydantic(db_case)
    priority = pydantic_case.calculate_priority()

    # 3. Actualizar datos (Sin commit todavía para evitar bloqueos)
    db_case.priority = priority.value
    db_case.status = CaseStatus.IN_REVIEW.value

    if priority == TriagePriority.P1_IMMEDIATE:
        db_case.status = CaseStatus.ESCALATED.value
        db_case.resolved_at = datetime.utcnow()

    # 4. Generar recomendación de IA
    # Si esto falla, lanzará una excepción y el status NO se guardará en la DB
    recommendation = await generate_triage_recommendation(db_case, db)
    db_case.ai_recommendation = recommendation

    # 5. COMMIT ÚNICO FINAL
    # Solo guardamos si TODO el proceso (incluyendo la IA) salió bien
    await db.commit()

    # Recargar para respuesta
    result = await db.execute(
        select(TriageCaseDB)
        .where(TriageCaseDB.id == case_id)
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one()
    return db_case_to_pydantic(db_case)