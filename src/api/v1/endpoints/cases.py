from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Importamos tus dependencias de seguridad y base de datos
from src.api.deps import get_db, get_current_active_patient, get_current_doctor
from src.models.enums import CaseStatus, TriagePriority
from src.models.db.patient_db import PatientDB
from src.models.triage import TriageCase, TriageCaseCreate
from src.models.symptom import Symptom

router = APIRouter(
    prefix="/cases",
    tags=["triage cases"],
)

@router.post(
    "/",
    response_model=TriageCase,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir un nuevo caso de triaje",
)
async def create_case(
    case_data: TriageCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    # SEGURIDAD: Forzamos que el paciente del caso sea el usuario autenticado
    # Ignoramos cualquier patient_id que el usuario intente enviar en el JSON
    new_case = TriageCase(
        patient_id=current_user.id,
        chief_complaint=case_data.chief_complaint,
        status=CaseStatus.OPEN
    )
    
    db.add(new_case)
    await db.flush()  # Generamos el ID del caso

    # Mapeo explícito de síntomas para evitar inyección de datos
    symptoms = [
        Symptom(
            description=s.description,
            severity=s.severity,
            duration_hours=s.duration_hours,
            body_location=s.body_location,
            is_worsening=s.is_worsening,
            case_id=new_case.id
        )
        for s in case_data.symptoms
    ]
    
    db.add_all(symptoms)
    await db.commit()
    await db.refresh(new_case)
    return new_case

@router.get(
    "/{case_id}",
    response_model=TriageCase,
    summary="Ver detalles del caso",
)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    result = await db.execute(select(TriageCase).where(TriageCase.id == case_id))
    case = result.scalars().first()

    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    
    # SEGURIDAD: Un paciente NO puede ver casos de otros pacientes (IDOR protection)
    if case.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este caso")
        
    return case

@router.post(
    "/{case_id}/evaluate",
    response_model=TriageCase,
    summary="Ejecutar algoritmo de triaje",
)
async def evaluate_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: PatientDB = Depends(get_current_active_patient),
) -> TriageCase:
    result = await db.execute(select(TriageCase).where(TriageCase.id == case_id))
    case = result.scalars().first()

    # Validación de existencia y propiedad
    if not case or case.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.status != CaseStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El caso ya está en estado: {case.status.value}"
        )

    # Ejecuta el protocolo START definido en tu modelo triage.py
    case.calculate_priority()

    if case.priority == TriagePriority.P1_IMMEDIATE:
        case.escalate()
    else:
        case.status = CaseStatus.IN_REVIEW

    await db.commit()
    await db.refresh(case)
    return case

@router.post(
    "/{case_id}/resolve",
    response_model=TriageCase,
    summary="Resolver caso (Solo Doctores)",
)
async def resolve_case(
    case_id: UUID,
    recommendation: str,
    db: AsyncSession = Depends(get_db),
    # SEGURIDAD: Cambiamos a get_current_doctor para que un paciente no se autorrecete
    current_user: PatientDB = Depends(get_current_doctor),
) -> TriageCase:
    result = await db.execute(select(TriageCase).where(TriageCase.id == case_id))
    case = result.scalars().first()

    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    if case.status != CaseStatus.IN_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El caso debe estar IN_REVIEW para ser resuelto"
        )

    case.resolve(recommendation)
    
    await db.commit()
    await db.refresh(case)
    return case