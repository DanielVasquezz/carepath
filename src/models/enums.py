from enum import Enum


class SeverityLevel(str, Enum):
    """
    Clinical severity level of a reported symptom.
    Inherits from str for automatic JSON serialization.

    Used by: Symptom, TriageCase
    """
    LOW = "low"           # monitor at home, no immediate action
    MODERATE = "moderate" # medical appointment within 24-48 hours
    HIGH = "high"         # urgent care required today
    CRITICAL = "critical" # emergency room immediately, call 911

class TriagePriority(str, Enum):
    """
    Priority level assigned to a triage case.
    
    Based on the START triage protocol — the international
    standard used by emergency medical services worldwide.
    
    P1 = most urgent / P4 = least urgent
    Used by: TriageCase.calculate_priority()
    """
    
    P1_IMMEDIATE = "P1_immediate"
    P2_URGENT    = "P2_urgent"
    P3_DELAYED   = "P3_delayed"
    P4_MINIMAL   = "P4_minimal"

class CaseStatus(str, Enum):
    """
    Lifecycle states of a triage case.
    
    A case always moves FORWARD through states — never backwards.
    This is called a State Machine — a pattern used in every
    serious business application.
    
    Valid transitions:
        OPEN → IN_REVIEW → RESOLVED
        OPEN → IN_REVIEW → ESCALATED
    """

    OPEN = "open"           # new case, not yet reviewed
    IN_REVIEW = "in_review" # clinician is actively reviewing
    RESOLVED = "resolved"   # case closed, no further action needed
    ESCALATED = "escalated" # transferred to human clinician for urgent review
    
class UserRole(str, Enum):
        """
    Roles within the CarePath system.
    
    Determines what each user can SEE and DO.
    This is called Role-Based Access Control (RBAC) —
    the industry standard for authorization in medical systems.
    
    PATIENT  → can only see their own cases
    DOCTOR   → can see assigned cases, write recommendations  
    ADMIN    → full system access, audit logs
    """
        PATIENT = "patient"
        DOCTOR  = "doctor"
        ADMIN   = "admin"