# src/models/db/patient_db.py
"""
CarePath — Patient Database Model
===================================
SQLAlchemy model defining the 'patients' table structure.

IMPORTANT: This is separate from src/models/patient.py
  src/models/patient.py  → Pydantic model (API validation, serialization)
  src/models/db/patient_db.py → SQLAlchemy model (database table structure)

Why separate?
Because they have different jobs. The Pydantic model validates
HTTP requests and formats HTTP responses. The SQLAlchemy model
maps to database tables and handles persistence.
In a production system, these concerns must be separated.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PatientDB(Base):
    """
    Database table: patients

    Mapped columns use Python types with SQLAlchemy's
    Mapped[] annotation system (SQLAlchemy 2.0 style).
    This gives type safety at the ORM level.
    """
    __tablename__ = "patients"
    # __tablename__ tells SQLAlchemy what the table is called
    # in the actual database. Convention: plural, snake_case.

    # ── Primary Key ──────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # UUID primary key — same reasoning as in Pydantic model:
    # no sequential IDs that reveal business information

    # ── Personal Information ─────────────────────────────────────
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        # unique=True → database enforces no duplicate emails
        # index=True  → creates a B-tree index on this column
        # Every time you search by email (login), PostgreSQL
        # uses the index instead of scanning the entire table.
        # Without index: O(n) scan. With index: O(log n).
        # For a table with 1 million patients, this is the
        # difference between 1ms and 1000ms per login query.
    )
    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # ── Authentication ───────────────────────────────────────────
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        # We never store plain text passwords. Ever.
        # bcrypt hash of the password lives here.
        # Length 255 because bcrypt output is always 60 chars
        # but 255 gives room for future hash algorithm changes.
    )

    # ── System Fields ────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="patient",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        # Index because every query filters by is_active=True
        # Soft delete: active patients only in normal queries
    )

    # ── Timestamps ───────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        # server_default=func.now() → the DATABASE sets this timestamp
        # not Python. Why? Because the DB server's clock is the
        # single source of truth. Multiple API servers might have
        # slightly different clocks. The DB clock never drifts.
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        # onupdate=func.now() → automatically updates this timestamp
        # every time any field on this row changes.
        # No need to manually set updated_at in your code.
    )
    
