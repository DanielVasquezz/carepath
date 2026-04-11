from enum import Enum


# ─────────────────────────────────────────────
# SEVERITY LEVEL
# ─────────────────────────────────────────────
class SeverityLevel(str, Enum):
    """
    Clinical severity level of a reported symptom.
    Used to determine urgency of medical attention.
    """

    LOW = "low"           # monitor at home
    MODERATE = "moderate" # appointment within 24-48h
    HIGH = "high"         # urgent care same day
    CRITICAL = "critical" # emergency care immediately


# ─────────────────────────────────────────────
# TRIAGE PRIORITY (START PROTOCOL)
# ─────────────────────────────────────────────
class TriagePriority(str, Enum):
    """
    Priority level assigned using START triage protocol.

    P1 = highest urgency
    P4 = lowest urgency
    """

    P1_IMMEDIATE = "P1_immediate"
    P2_URGENT    = "P2_urgent"
    P3_DELAYED   = "P3_delayed"
    P4_MINIMAL   = "P4_minimal"


# ─────────────────────────────────────────────
# CASE STATUS (STATE MACHINE)
# ─────────────────────────────────────────────
class CaseStatus(str, Enum):
    """
    Lifecycle of a triage case.

    OPEN → IN_REVIEW → RESOLVED / ESCALATED
    """

    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ─────────────────────────────────────────────
# USER ROLES (RBAC)
# ─────────────────────────────────────────────
class UserRole(str, Enum):
    """
    Role-Based Access Control (RBAC) system.

    PATIENT → own data only
    DOCTOR  → assigned cases
    ADMIN   → full system access
    """

    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"