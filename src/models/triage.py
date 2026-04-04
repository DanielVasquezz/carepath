from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field

from src.models.enums import CaseStatus, SeverityLevel, TriagePriority
from src.models.symptom import Symptom, SymptomCreate


class TriageCaseCreate(BaseModel):
    """
    Data required to open a new triage case.
    Received by: POST /api/v1/cases
    """
    patient_id: UUID = Field(
        ...,
        description="The patient opening this case"
    )
    chief_complaint: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Main reason the patient is seeking care"
    )
    symptoms: list[SymptomCreate] = Field(
        ...,
        min_length=1,
        description="At least one symptom required to open a case"
    )


class TriageCase(BaseModel):
    """
    Central entity that orchestrates CarePath's triage process.

    State machine:
        OPEN → IN_REVIEW → RESOLVED
        OPEN → IN_REVIEW → ESCALATED

    A case never moves backwards. Medical records are permanent.
    """
    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID = Field(..., description="Patient who opened this case")
    chief_complaint: str = Field(..., min_length=10, max_length=500)
    symptoms: list[Symptom] = Field(default_factory=list)
    status: CaseStatus = Field(default=CaseStatus.OPEN)
    priority: Optional[TriagePriority] = Field(default=None)
    ai_recommendation: Optional[str] = Field(default=None)
    attending_doctor_id: Optional[UUID] = Field(default=None)
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None)

    @computed_field
    @property
    def total_risk_score(self) -> int:
        """Sum of risk_score across all symptoms."""
        return sum(symptom.risk_score for symptom in self.symptoms)

    @computed_field
    @property
    def has_critical_symptom(self) -> bool:
        """True if ANY symptom is CRITICAL — triggers P1 immediately."""
        return any(
            symptom.severity == SeverityLevel.CRITICAL
            for symptom in self.symptoms
        )

    def calculate_priority(self) -> TriagePriority:
        """
        START triage protocol implementation.
        Side effects: sets self.priority, transitions to IN_REVIEW.
        """
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
        """
        Closes the case with a recommendation.
        Transition: IN_REVIEW → RESOLVED
        """
        self.ai_recommendation = recommendation
        self.status = CaseStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def escalate(self) -> None:
        """
        Escalates to emergency services.
        Transition: IN_REVIEW → ESCALATED
        Irreversible.
        """
        self.status = CaseStatus.ESCALATED
        self.priority = TriagePriority.P1_IMMEDIATE
        self.resolved_at = datetime.utcnow()

    @property
    def resolution_time_minutes(self) -> Optional[float]:
        """Minutes between opening and resolution. None if still open."""
        if self.resolved_at is None:
            return None
        delta = self.resolved_at - self.opened_at
        return delta.total_seconds() / 60

    model_config = {"from_attributes": True}