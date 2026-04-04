from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from src.models.enums import SeverityLevel


class SymptomCreate(BaseModel):
    """
    Data received from the API when a patient reports a symptom.
    Received by: POST /api/v1/cases/{case_id}/symptoms
    Designed around how patients actually describe symptoms —
    in natural language, with perceived severity and duration.
    The AI engine later interprets this into clinical terms.
    """

    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Natural language description in the patient's own words"
    )
    
    severity: SeverityLevel = Field(
        ...,
        description="Patient's perceived intensity of the symptom"
    )
    duration_hours: Optional[float] = Field(
        default=None,
        ge=0,
        le=8760,
        description="How long the patient has had this symptom in hours"
    )

    body_location: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Body area affected: 'chest', 'head', 'abdomen', 'left arm'"
    )

    is_worsening: bool = Field(
        default=False,
        description="Whether the symptom is actively getting worse over time"
    )


    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str) -> str:
        """
        Normalizes whitespace in symptom descriptions.
        
         "I   have    a    headache" → "I have a headache"
        
        Why? Because the AI engine tokenizes text by spaces.
        Extra whitespace creates noise that reduces accuracy.
        Cleaning input before it reaches the AI is standard practice.
        """
        return " ".join(v.strip().split())

class Symptom(SymptomCreate):
    """
    Complete symptom as stored in the system.
    Extends SymptomCreate with system-generated fields.
    
    The risk_score property is the numerical output that
    feeds directly into TriageCase.calculate_priority().
    This is where patient language becomes medical math.
    """
    id: UUID = Field(default_factory=uuid4)

    case_id: UUID = Field(
        ...,
        description="The triage case this symptom belongs to"
    )
    reported_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Exact moment the symptom was reported — UTC always"
    )

    @property
    def risk_score(self) -> int:
        """
        Converts clinical observations into a numerical score.
        This score feeds into TriageCase.calculate_priority().
        
        Scoring logic:
            Base score from severity:
                LOW      = 1
                MODERATE = 2
                HIGH     = 3
                CRITICAL = 4
            
            Modifiers:
                # +2 if symptom is actively worsening/
                +1 if duration exceeds 24 hours
        
        Maximum possible score: 7 (CRITICAL + worsening + long duration)
        Minimum possible score: 1 (LOW + stable + recent)
        
        Why a property and not a stored field?
        Because risk_score depends on other fields. If the doctor
        updates severity, risk_score updates automatically.
        A stored field would go stale. A property is always current.
        """
        base_scores = {
            SeverityLevel.LOW:      1,
            SeverityLevel.MODERATE: 2,
            SeverityLevel.HIGH:     3,
            SeverityLevel.CRITICAL: 4,
        }
        score = base_scores[self.severity]

        if self.is_worsening:
            score += 2

        if self.duration_hours and self.duration_hours > 24:
            score += 1

        return score

    model_config = {"from_attributes": True}