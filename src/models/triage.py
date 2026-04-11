from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from src.models.enums import CaseStatus, SeverityLevel, TriagePriority


# ─────────────────────────────────────────────
# SYMPTOM SCHEMAS
# ─────────────────────────────────────────────
class SymptomBase(BaseModel):
    description: str = Field(..., example="Dolor agudo en el pecho")
    severity: SeverityLevel
    duration_hours: Optional[float] = Field(None, ge=0)
    body_location: Optional[str] = None
    is_worsening: bool = False


class SymptomCreate(SymptomBase):
    pass


class Symptom(SymptomBase):
    id: UUID
    case_id: UUID
    reported_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# TRIAGE CASE CREATE
# ─────────────────────────────────────────────
class TriageCaseCreate(BaseModel):
    """
    Data required to open a new triage case.
    """
    patient_id: Optional[UUID] = Field(
        default=None,
        description="Ignored — taken from JWT token"
    )

    chief_complaint: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Main reason for consultation"
    )

    symptoms: list[SymptomCreate] = Field(
        ...,
        min_length=1,
        description="At least one symptom required"
    )


# ─────────────────────────────────────────────
# TRIAGE CASE (DOMAIN MODEL)
# ─────────────────────────────────────────────
class TriageCase(BaseModel):
    """
    Central entity for CarePath triage system.

    State machine:
        OPEN → IN_REVIEW → RESOLVED / ESCALATED
    """

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID

    chief_complaint: str
    symptoms: list[Symptom] = Field(default_factory=list)

    status: CaseStatus = Field(default=CaseStatus.OPEN)
    priority: Optional[TriagePriority] = None

    ai_recommendation: Optional[str] = None
    attending_doctor_id: Optional[UUID] = None

    opened_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    # ─────────────────────────────────────────────
    # COMPUTED FIELDS
    # ─────────────────────────────────────────────
    @computed_field
    @property
    def total_risk_score(self) -> int:
        """
        Sum of severity scores:
        LOW=1, MODERATE=2, HIGH=3, CRITICAL=4
        """
        score_map = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MODERATE: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }

        return sum(score_map.get(s.severity, 1) for s in self.symptoms)

    @computed_field
    @property
    def has_critical_symptom(self) -> bool:
        return any(
            s.severity == SeverityLevel.CRITICAL
            for s in self.symptoms
        )

    # ─────────────────────────────────────────────
    # BUSINESS LOGIC (START)
    # ─────────────────────────────────────────────
    def calculate_priority(self) -> TriagePriority:
        if self.has_critical_symptom:
            priority = TriagePriority.P1_IMMEDIATE
        elif self.total_risk_score >= 8:
            priority = TriagePriority.P2_URGENT
        elif self.total_risk_score >= 4:
            priority = TriagePriority.P3_DELAYED
        else:
            priority = TriagePriority.P4_MINIMAL

        self.priority = priority
        self.status = CaseStatus.IN_REVIEW
        return priority

    def resolve(self, recommendation: str) -> None:
        self.ai_recommendation = recommendation
        self.status = CaseStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def escalate(self) -> None:
        self.status = CaseStatus.ESCALATED
        self.priority = TriagePriority.P1_IMMEDIATE
        self.resolved_at = datetime.utcnow()

    @property
    def resolution_time_minutes(self) -> Optional[float]:
        if not self.resolved_at:
            return None
        return (self.resolved_at - self.opened_at).total_seconds() / 60

    model_config = {"from_attributes": True}