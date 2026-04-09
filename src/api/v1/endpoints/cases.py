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
from uuid import UUID

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

    Why this function exists:
    SQLAlchemy models handle persistence.
    Pydantic models handle API responses.
    This converter is the bridge between the two worlds.
    Without it, FastAPI cannot serialize the response correctly.
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

    SECURITY: patient_id is taken from the JWT token — not from
    the request body. A patient cannot open a case for another patient.
    This prevents IDOR (Insecure Direct Object Reference) attacks.
    """
    # Create the case in the database
    db_case = TriageCaseDB(
        patient_id=current_user.id,  # from JWT — not from request body
        chief_complaint=case_data.chief_complaint,
        status=CaseStatus.OPEN.value,
    )
    db.add(db_case)
    await db.flush()  # generates db_case.id without committing

    # Create symptoms linked to this case
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
    await db.flush()

    # Reload with symptoms for the response
    await db.refresh(db_case)
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

    SECURITY: Patients can only see their own cases.
    Accessing another patient's case returns 404 — not 403.
    Why 404 and not 403? Because returning 403 confirms the case
    exists. 404 reveals nothing about other patients' data.
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
    summary="Run START triage algorithm",
)
async def evaluate_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    """
    POST /api/v1/cases/{case_id}/evaluate

    Runs the START triage protocol on the case symptoms.
    Converts DB model → Pydantic model → runs algorithm →
    saves results back to DB.
    """
    # Load case with symptoms from DB
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

    if db_case.status != CaseStatus.OPEN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Case is already {db_case.status} — cannot re-evaluate",
        )

    # Convert to Pydantic to run the algorithm
    pydantic_case = db_case_to_pydantic(db_case)
    priority = pydantic_case.calculate_priority()

    # Save results back to the DB model
    db_case.priority = priority.value
    db_case.status = CaseStatus.IN_REVIEW.value

    # Auto-escalate P1 cases
    if priority == TriagePriority.P1_IMMEDIATE:
        from datetime import datetime
        db_case.status = CaseStatus.ESCALATED.value
        db_case.resolved_at = datetime.utcnow()

    await db.commit()

    # Reload for response
    result = await db.execute(
        select(TriageCaseDB)
        .where(TriageCaseDB.id == case_id)
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one()
    return db_case_to_pydantic(db_case)


@router.post(
    "/{case_id}/resolve",
    response_model=TriageCase,
    summary="Resolve case with recommendation — doctors only",
)
async def resolve_case(
    case_id: UUID,
    recommendation: str,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_doctor),
    # RBAC: only doctors can resolve cases
    # A patient cannot write their own medical recommendation
) -> TriageCase:
    """
    POST /api/v1/cases/{case_id}/resolve

    RBAC: restricted to DOCTOR role.
    Patients cannot self-prescribe recommendations.
    """
    result = await db.execute(
        select(TriageCaseDB)
        .where(TriageCaseDB.id == case_id)
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one_or_none()

    if db_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    if db_case.status != CaseStatus.IN_REVIEW.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case must be IN_REVIEW before resolving",
        )

    from datetime import datetime
    db_case.ai_recommendation = recommendation
    db_case.status = CaseStatus.RESOLVED.value
    db_case.resolved_at = datetime.utcnow()
    db_case.attending_doctor_id = current_user.id

    await db.commit()

    result = await db.execute(
        select(TriageCaseDB)
        .where(TriageCaseDB.id == case_id)
        .options(selectinload(TriageCaseDB.symptoms))
    )
    db_case = result.scalar_one()
    return db_case_to_pydantic(db_case)