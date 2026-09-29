"""Deterministically understand and structure citizen complaints."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class IssueRule:
    """Keyword rules and output metadata for one supported civic issue."""

    category: str
    issue: str
    risk: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class ClassificationResult:
    """Explainable result from deterministic complaint classification."""

    category: str
    issue: str
    severity: str
    risk: str
    confidence: float
    reasons: tuple[str, ...]


ISSUE_RULES: tuple[IssueRule, ...] = (
    IssueRule(
        category="Road Damage",
        issue="Pothole",
        risk="Accident Risk",
        patterns=(
            "pothole",
            "pot hole",
            "hole in road",
            "hole in the road",
            "hole on road",
            "hole on the road",
            "road hole",
        ),
    ),
    IssueRule(
        category="Waste Management",
        issue="Garbage Accumulation",
        risk="Public Health Risk",
        patterns=("garbage", "trash", "waste", "rubbish", "dumping", "dumped"),
    ),
    IssueRule(
        category="Drainage",
        issue="Blocked/Overflowing Drain",
        risk="Flooding / Public Health Risk",
        patterns=(
            "blocked drain",
            "overflowing drain",
            "drain overflow",
            "drainage",
            "drain",
            "sewer",
            "sewage",
        ),
    ),
    IssueRule(
        category="Water Supply",
        issue="Water Leakage",
        risk="Water Loss / Infrastructure Risk",
        patterns=(
            "water leak",
            "water leakage",
            "water pipe",
            "leaking pipe",
            "broken pipe",
            "broken water pipe",
            "burst pipe",
            "water flowing",
        ),
    ),
    IssueRule(
        category="Streetlight",
        issue="Streetlight Failure",
        risk="Visibility / Public Safety Risk",
        patterns=(
            "streetlight",
            "streetlamp",
            "street light",
            "street lamp",
            "lamp",
            "lamp post",
            "light not working",
            "light is not working",
            "dark street",
            "dark at night",
        ),
    ),
    IssueRule(
        category="Road Damage",
        issue="General Road Damage",
        risk="Accident Risk",
        patterns=(
            "road damage",
            "damaged road",
            "broken road",
            "cracked road",
            "road crack",
            "bad road",
        ),
    ),
)

CRITICAL_INDICATORS: tuple[str, ...] = (
    "injury",
    "injuries",
    "electrocution",
    "electric shock",
    "exposed electrical",
    "exposed wire",
    "life threatening",
)

HIGH_URGENCY_INDICATORS: tuple[str, ...] = (
    "accident",
    "dangerous",
    "severe",
    "huge",
    "major",
    "flooded",
    "overflowing",
    "blocking",
    "blocked",
    "school",
    "hospital",
    "highway",
    "main road",
)

LOW_SEVERITY_INDICATORS: tuple[str, ...] = ("small", "minor", "slight")


def normalize_description(description: str) -> str:
    """Normalize case, punctuation, and whitespace for reliable phrase matching."""

    normalized = re.sub(r"[^a-z0-9\s]", " ", description.casefold())
    return " ".join(normalized.split())


def _matched_phrases(text: str, patterns: tuple[str, ...]) -> tuple[str, ...]:
    """Return complete word or phrase matches in configuration order."""

    return tuple(
        pattern
        for pattern in patterns
        if re.search(rf"(?:^|\s){re.escape(pattern)}(?:$|\s)", text)
    )


def _rule_confidence(match_count: int) -> float:
    """Convert rule evidence count into a documented deterministic score."""

    if match_count >= 3:
        return 0.95
    if match_count == 2:
        return 0.80
    if match_count == 1:
        return 0.65
    return 0.0


def _severity_for(text: str, classified: bool) -> tuple[str, tuple[str, ...]]:
    """Determine severity from explicit urgency language."""

    critical_matches = _matched_phrases(text, CRITICAL_INDICATORS)
    if critical_matches:
        return "Critical", critical_matches

    high_matches = _matched_phrases(text, HIGH_URGENCY_INDICATORS)
    if high_matches:
        return "High", high_matches

    low_matches = _matched_phrases(text, LOW_SEVERITY_INDICATORS)
    if low_matches:
        return "Low", low_matches

    return ("Medium", ()) if classified else ("Low", ())


def classify_complaint(description: str) -> ClassificationResult:
    """Classify a complaint using explainable keyword and phrase rules."""

    normalized = normalize_description(description)
    matches_by_rule = [
        (rule, _matched_phrases(normalized, rule.patterns)) for rule in ISSUE_RULES
    ]
    rule, matches = max(matches_by_rule, key=lambda item: len(item[1]))

    if not matches:
        return ClassificationResult(
            category="Other",
            issue="Unclassified",
            severity="Low",
            risk="Undetermined Risk",
            confidence=0.0,
            reasons=("No supported civic issue indicators were matched.",),
        )

    severity, severity_matches = _severity_for(normalized, classified=True)
    reasons = [
        f"Matched {rule.issue} indicator(s): {', '.join(matches)}.",
        f"Rule-match confidence is based on {len(matches)} matched issue indicator(s).",
    ]
    if severity_matches:
        reasons.append(
            f"Severity is {severity} due to: {', '.join(severity_matches)}."
        )
    else:
        reasons.append("Severity defaults to Medium because no urgency modifier was found.")

    return ClassificationResult(
        category=rule.category,
        issue=rule.issue,
        severity=severity,
        risk=rule.risk,
        confidence=_rule_confidence(len(matches)),
        reasons=tuple(reasons),
    )
