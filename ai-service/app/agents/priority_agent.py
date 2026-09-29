"""Calculate explainable civic issue priority from available evidence."""

from dataclasses import dataclass
import re

from app.agents.complaint_agent import ClassificationResult, normalize_description
from app.models.schemas import ComplaintInput


@dataclass(frozen=True)
class PriorityResult:
    """Priority level, numeric score, and its human-readable explanation."""

    priority: str
    score: int
    reasons: tuple[str, ...]


SEVERITY_SCORES: dict[str, int] = {
    "Low": 10,
    "Medium": 35,
    "High": 60,
    "Critical": 85,
}

RISK_INDICATORS: tuple[str, ...] = (
    "accident",
    "dangerous",
    "injury",
    "injuries",
    "flooded",
    "overflowing",
    "blocking",
    "blocked",
    "electrocution",
    "exposed wire",
    "exposed electrical",
)

SENSITIVE_LOCATION_INDICATORS: tuple[str, ...] = (
    "school",
    "hospital",
    "highway",
    "main road",
)


def _matched_phrases(text: str, patterns: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        pattern
        for pattern in patterns
        if re.search(rf"(?:^|\s){re.escape(pattern)}(?:$|\s)", text)
    )


def _citizen_count_points(citizen_count: int) -> int:
    if citizen_count >= 10:
        return 15
    if citizen_count >= 3:
        return 8
    if citizen_count >= 2:
        return 4
    return 0


def _priority_for_score(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def calculate_priority(
    complaint: ComplaintInput,
    classification: ClassificationResult,
) -> PriorityResult:
    """Score priority using only evidence available in the current request."""

    score = SEVERITY_SCORES[classification.severity]
    reasons = [
        f"{classification.severity} severity contributes {score} points."
    ]
    normalized = normalize_description(complaint.description)

    risk_matches = _matched_phrases(normalized, RISK_INDICATORS)
    if risk_matches:
        risk_points = min(15, len(risk_matches) * 5)
        score += risk_points
        reasons.append(
            f"Risk indicator(s) {', '.join(risk_matches)} contribute {risk_points} points."
        )

    location_matches = _matched_phrases(normalized, SENSITIVE_LOCATION_INDICATORS)
    if location_matches:
        score += 10
        reasons.append(
            f"Sensitive location context ({', '.join(location_matches)}) contributes 10 points."
        )

    citizen_points = _citizen_count_points(complaint.citizen_count)
    if citizen_points:
        score += citizen_points
        reasons.append(
            f"A citizen count of {complaint.citizen_count} contributes {citizen_points} points."
        )

    score = min(score, 100)
    priority = _priority_for_score(score)
    reasons.append(f"Final score {score}/100 maps to {priority} priority.")
    return PriorityResult(priority=priority, score=score, reasons=tuple(reasons))
