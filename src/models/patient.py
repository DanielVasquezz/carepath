from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models.enums import UserRole


class PatientBase(BaseModel):
    """
    Base fields shared between PatientCreate and Patient.

    Why three classes (PatientBase, PatientCreate, Patient)?
    This is the DTO pattern — Data Transfer Object.

    PatientBase   → shared fields, no sensitive data
    PatientCreate → what arrives FROM the API (includes password)
    Patient       → what lives IN the system (no password, has ID)

    This prevents accidentally exposing the hashed password
    in API responses. A mistake that has caused real data breaches.
    """
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Patient's first name"
    )
    last_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Patient's last name"
    )
    email: EmailStr = Field(
        ...,
        description="Contact email and login identifier"
    )
    date_of_birth: date = Field(
        ...,
        description="Used to calculate age and validate pediatric protocols"
    )
    phone: Optional[str] = Field(
        default=None,
        pattern=r'^\+?[1-9]\d{7,14}$',
        description="Contact number with optional country code"
    )

    @field_validator("first_name", "last_name")
    @classmethod
    def capitalize_names(cls, v: str) -> str:
        """
        Normalizes names automatically.
        "JUAN CARLOS" → "Juan Carlos"
        "maría"       → "María"
        Prevents duplicate patients caused by capitalization differences.
        """
        return v.strip().title()

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date(cls, v: date) -> date:
        """
        Guards against impossible birth dates.
        Catches data entry errors before they corrupt the DB.
        """
        today = date.today()
        if v > today:
            raise ValueError("Date of birth cannot be in the future")
        age_in_days = (today - v).days
        if age_in_days > 150 * 365:
            raise ValueError("Date of birth is not valid")
        return v


class PatientCreate(PatientBase):
    """
    Data required to register a new patient.
    Received by: POST /api/v1/patients

    The password arrives in plain text here.
    The AuthService hashes it with bcrypt before
    it ever touches the database.
    """
    password: str = Field(
        ...,
        min_length=8,
        description="Plain text — hashed by AuthService before storage"
    )


class Patient(PatientBase):
    """
    Complete patient as it exists within the system.
    Returned by: GET /api/v1/patients/{id}

    Never contains password — that lives only in the DB.
    """
    id: UUID = Field(
        default_factory=uuid4,
        description="Auto-generated unique identifier"
    )
    role: UserRole = Field(
        default=UserRole.PATIENT
    )
    is_active: bool = Field(
        default=True,
        description="False = soft deleted. Medical records are never erased."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    @property
    def age(self) -> int:
        """Calculated from date_of_birth. Never stored in DB."""
        return (date.today() - self.date_of_birth).days // 365

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_minor(self) -> bool:
        """Minors require pediatric protocols and parental consent."""
        return self.age < 18

    @classmethod
    def create_emergency_patient(
        cls,
        first_name: str,
        last_name: str
    ) -> Patient:
        """
        Factory Method — creates a temporary patient for emergencies.
        No time for full registration when lives are at stake.
        """
        temp_id = uuid4()
        return cls(
            first_name=first_name,
            last_name=last_name,
            email=f"emergency_{temp_id}@carepath.temp",
            date_of_birth=date(2000, 1, 1),
        )

    model_config = {
        "from_attributes": True
    }