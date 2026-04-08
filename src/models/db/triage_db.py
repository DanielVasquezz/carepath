# src/models/db/triage_db.py
"""
CarePath — Triage Database Models
===================================
SQLAlchemy models for TriageCase and Symptom tables.

Relationships:
  patients 1──< triage_cases   (one patient, many cases)
  triage_cases 1──< symptoms   (one case, many symptoms)

These are foreign key relationships — the database enforces
referential integrity. You cannot create a triage_case for
a patient_id that doesn't exist in the patients table.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class SymptomDB(Base):
    """
    Database table: symptoms

    Each symptom belongs to exactly one triage case.
    A triage case can have many symptoms.
    """
    __tablename__ = "symptoms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        # ForeignKey → this column references triage_cases.id
        # ondelete="CASCADE" → if the case is deleted,
        # all its symptoms are deleted automatically.
        # Without CASCADE, deleting a case would fail
        # because orphaned symptoms would still reference it.
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Text = unlimited length string in PostgreSQL
    # Use Text for user-written content, String(n) for codes/names

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_worsening: Mapped[bool] = mapped_column(Boolean, default=False)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # ── Relationship ─────────────────────────────────────────────
    case: Mapped["TriageCaseDB"] = relationship(
        back_populates="symptoms"
    )
    # This creates a Python attribute 'case' on SymptomDB
    # symptom.case → gives you the TriageCaseDB object
    # SQLAlchemy handles the JOIN query automatically


class TriageCaseDB(Base):
    """
    Database table: triage_cases

    Central table linking patients to their triage evaluations.
    """
    __tablename__ = "triage_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        # ondelete="RESTRICT" → cannot delete a patient
        # who has triage cases. Medical records must be
        # preserved even after account closure.
        # This enforces the soft-delete pattern at DB level.
    )
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
        # Indexed because dashboards frequently filter by status
        # "show me all OPEN cases" runs this query constantly
    )
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    attending_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────
    symptoms: Mapped[list["SymptomDB"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
        # lazy="selectin" → when you load a TriageCaseDB,
        # SQLAlchemy automatically loads its symptoms
        # using a second SELECT query (not a JOIN).
        # In async SQLAlchemy, selectin is the recommended
        # loading strategy — it works well with async sessions.
    )