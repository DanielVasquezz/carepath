"""
CarePath — START Triage Logic
==============================
Implementation of a simplified START triage scoring system.
"""

from src.models.db.triage_db import SymptomDB
from src.models.enums import SeverityLevel, TriagePriority


def run_start_triage(symptoms: list[SymptomDB]) -> tuple[TriagePriority, int]:
    """
    Calculates:
        - Triage priority (P1–P4)
        - Total risk score

    Scoring system:
        LOW=1, MODERATE=2, HIGH=3, CRITICAL=4
        +2 if worsening
        +1 if duration > 24h
    """

    base_scores = {
        SeverityLevel.LOW.value: 1,
        SeverityLevel.MODERATE.value: 2,
        SeverityLevel.HIGH.value: 3,
        SeverityLevel.CRITICAL.value: 4,
    }

    total_score = 0
    has_critical = False

    for s in symptoms:

        # ── normalize severity safely
        sev = s.severity.value if hasattr(s.severity, "value") else s.severity

        if sev == SeverityLevel.CRITICAL.value:
            has_critical = True

        score = base_scores.get(sev, 1)

        # ── modifiers
        if s.is_worsening:
            score += 2

        if s.duration_hours and s.duration_hours > 24:
            score += 1

        total_score += score

    # ── START decision rules
    if has_critical:
        return TriagePriority.P1_IMMEDIATE, total_score

    if total_score >= 8:
        return TriagePriority.P2_URGENT, total_score

    if total_score >= 4:
        return TriagePriority.P3_DELAYED, total_score

    return TriagePriority.P4_MINIMAL, total_score