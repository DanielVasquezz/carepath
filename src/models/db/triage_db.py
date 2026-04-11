"""
CarePath — Triage Database Models
===================================
SQLAlchemy models for TriageCase and Symptom tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from src.core.database import Base


# ─────────────────────────────────────────────
# SYMPTOM MODEL
# ─────────────────────────────────────────────
class SymptomDB(Base):
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
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_worsening: Mapped[bool] = mapped_column(Boolean, default=False)

    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Embedding vector (pgvector)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    # Relationship
    case: Mapped["TriageCaseDB"] = relationship(
        back_populates="symptoms"
    )


# ─────────────────────────────────────────────
# TRIAGE CASE MODEL
# ─────────────────────────────────────────────
class TriageCaseDB(Base):
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
    )

    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
    )

    priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

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

    # Relationship (async-safe)
    symptoms: Mapped[list[SymptomDB]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="selectin",
    )