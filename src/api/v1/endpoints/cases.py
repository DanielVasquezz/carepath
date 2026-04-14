from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.deps import get_current_active_patient
from src.core.database import get_db

from src.models.db.patient_db import PatientDB
from src.models.db.triage_db import TriageCaseDB, SymptomDB

from src.models.enums import CaseStatus, TriagePriority

from src.models.symptom import Symptom
from src.models.triage import TriageCase, TriageCaseCreate

from src.services.triage_logic import run_start_triage
from src.services.ai_service import (
    generate_triage_recommendation,
    generate_symptom_embeddings,
    validate_risk_score,
)

router = APIRouter(prefix="/cases", tags=["triage cases"])


# =========================
# MAPPER SAFE
# =========================
def db_case_to_pydantic(db_case: TriageCaseDB) -> TriageCase:
    return TriageCase(
        id=db_case.id,
        patient_id=db_case.patient_id,
        chief_complaint=db_case.chief_complaint,
        symptoms=[
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
        ],
        status=db_case.status,
        priority=db_case.priority,
        ai_recommendation=db_case.ai_recommendation,
        attending_doctor_id=db_case.attending_doctor_id,
        opened_at=db_case.opened_at,
        resolved_at=db_case.resolved_at,
    )


# =========================
# CREATE CASE (🔥 CON START)
# =========================
@router.post("/", response_model=TriageCase, status_code=201)
async def create_case(
    case_data: TriageCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
):
    try:
        # 1. Crear caso
        db_case = TriageCaseDB(
            patient_id=current_user.id,
            chief_complaint=case_data.chief_complaint,
            status=CaseStatus.IN_REVIEW.value,  # 🔥 ya entra evaluado
        )

        db.add(db_case)
        await db.flush()

        # 2. Crear síntomas
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

        # 3. START TRIAGE (SIN IA)
        priority_enum, score = run_start_triage(db_symptoms)

        db_case.priority = priority_enum.value
        db_case.ai_recommendation = (
            f"Sistema START: Score {score}. "
            f"Prioridad calculada automáticamente."
        )

        # 4. Embeddings (no bloqueante)
        try:
            await generate_symptom_embeddings(db_symptoms)
        except Exception:
            pass

        # 5. Guardar
        await db.commit()

        # 6. Recargar relaciones
        result = await db.execute(
            select(TriageCaseDB)
            .where(TriageCaseDB.id == db_case.id)
            .options(selectinload(TriageCaseDB.symptoms))
        )

        db_case = result.scalar_one()

        return db_case_to_pydantic(db_case)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# EVALUATE CASE (🔥 HÍBRIDO REAL)
# =========================
@router.post("/{case_id}/evaluate", response_model=TriageCase)
async def evaluate_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
):
    result = await db.execute(
        select(TriageCaseDB)
        .where(
            TriageCaseDB.id == case_id,
            TriageCaseDB.patient_id == current_user.id,
        )
        .options(selectinload(TriageCaseDB.symptoms))
    )

    db_case = result.scalar_one_or_none()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        # =========================
        # 1. BASE START
        # =========================
        priority_enum, base_score = run_start_triage(db_case.symptoms)

        # =========================
        # 2. PAYLOAD IA
        # =========================
        ai_payload = {
            "id": str(db_case.id),
            "chief_complaint": db_case.chief_complaint,
            "symptoms": [
                {
                    "description": s.description,
                    "severity": s.severity,
                    "duration_hours": s.duration_hours,
                    "body_location": s.body_location,
                    "is_worsening": s.is_worsening,
                }
                for s in db_case.symptoms
            ],
        }

        # =========================
        # 3. IA
        # =========================
        ai_data = await generate_triage_recommendation(ai_payload)

        ai_score = ai_data.get("risk_score", base_score)

        # =========================
        # 4. VALIDACIÓN CRÍTICA
        # =========================
        symptoms_text = " ".join(
            s["description"] for s in ai_payload["symptoms"]
        )

        final_score = validate_risk_score(symptoms_text, ai_score)

        # =========================
        # 5. MAPEO PRIORIDAD
        # =========================
        if final_score >= 8:
            final_priority = TriagePriority.P1_IMMEDIATE
        elif final_score >= 6:
            final_priority = TriagePriority.P2_URGENT
        elif final_score >= 4:
            final_priority = TriagePriority.P3_DELAYED
        else:
            final_priority = TriagePriority.P4_MINOR

        db_case.priority = final_priority.value

        db_case.status = (
            CaseStatus.ESCALATED.value
            if final_priority == TriagePriority.P1_IMMEDIATE
            else CaseStatus.IN_REVIEW.value
        )

        # =========================
        # 6. RESULTADO FINAL
        # =========================
        db_case.ai_recommendation = (
            f"Score Riesgo: {final_score}\n\n"
            f"{ai_data.get('recommendation', 'Revisión manual.')}"
        )

        await db.commit()
        await db.refresh(db_case)

        return db_case_to_pydantic(db_case)

    except Exception:
        # =========================
        # FALLBACK SEGURO
        # =========================
        await db.rollback()

        db_case.status = CaseStatus.IN_REVIEW.value
        db_case.priority = TriagePriority.P3_DELAYED.value
        db_case.ai_recommendation = (
            "Score Riesgo: 0\n\nAI falló. Revisión manual requerida."
        )

        await db.commit()
        await db.refresh(db_case)

        return db_case_to_pydantic(db_case)