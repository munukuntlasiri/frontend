"""Fuse related reports using deterministic text, location, and issue signals."""

from difflib import SequenceMatcher
from math import asin, cos, radians, sin, sqrt
import re

from app.agents.complaint_agent import ClassificationResult, classify_complaint
from app.models.schemas import (
    CandidateSimilarity,
    ComplaintInput,
    MasterIssueCandidate,
)

EARTH_RADIUS_METERS = 6_371_000.0

# Maximum distance and score for each geographic evidence band.
LOCATION_SIMILARITY_BANDS: tuple[tuple[float, float], ...] = (
    (20.0, 1.0),
    (50.0, 0.85),
    (100.0, 0.55),
)
MAX_DUPLICATE_DISTANCE_METERS = LOCATION_SIMILARITY_BANDS[-1][0]

FUSION_WEIGHTS: dict[str, float] = {
    "text": 0.40,
    "location": 0.35,
    "compatibility": 0.25,
}

# Ready for a future Vision Agent signal without changing the scoring function.
FUSION_WEIGHTS_WITH_IMAGE: dict[str, float] = {
    "text": 0.30,
    "location": 0.25,
    "compatibility": 0.20,
    "image": 0.25,
}

DUPLICATE_THRESHOLD = 0.72

SYNONYM_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b(?:hole|holes)\s+(?:in|on)\s+(?:the\s+)?road\b", "pothole"),
    (r"\broad\s+(?:hole|holes)\b", "pothole"),
    (r"\bpot\s+hole\b", "pothole"),
    (r"\b(?:trash|rubbish|waste)\b", "garbage"),
    (r"\b(?:street\s+light|street\s+lamp|streetlamp)\b", "streetlight"),
    (
        r"\b(?:water\s+leak|water\s+leakage|leaking\s+pipe|broken\s+(?:water\s+)?pipe)\b",
        "waterleakage",
    ),
    (r"\bblocked\s+(?:sewer|drain)\b", "drainageproblem"),
    (r"\bhuge\b", "large"),
    (r"\bstopped\s+working\b", "not working"),
)

STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "be",
        "been",
        "beside",
        "by",
        "causing",
        "for",
        "has",
        "have",
        "in",
        "is",
        "may",
        "near",
        "of",
        "on",
        "our",
        "problems",
        "that",
        "the",
        "there",
        "this",
        "to",
        "with",
    }
)


def normalize_text_for_similarity(text: str) -> str:
    """Normalize civic synonyms and remove low-information words."""

    normalized = re.sub(r"[^a-z0-9\s]", " ", text.casefold())
    normalized = " ".join(normalized.split())
    for pattern, replacement in SYNONYM_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)
    tokens = [token for token in normalized.split() if token not in STOP_WORDS]
    return " ".join(tokens)


def calculate_text_similarity(first: str, second: str) -> float:
    """Combine token overlap and character sequence similarity without ML."""

    normalized_first = normalize_text_for_similarity(first)
    normalized_second = normalize_text_for_similarity(second)
    if not normalized_first or not normalized_second:
        return 0.0

    first_tokens = set(normalized_first.split())
    second_tokens = set(normalized_second.split())
    union = first_tokens | second_tokens
    jaccard = len(first_tokens & second_tokens) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, normalized_first, normalized_second).ratio()
    return round((0.60 * jaccard) + (0.40 * sequence), 4)


def haversine_distance_meters(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    """Calculate great-circle distance between two coordinates in meters."""

    first_lat = radians(first_latitude)
    second_lat = radians(second_latitude)
    latitude_delta = radians(second_latitude - first_latitude)
    longitude_delta = radians(second_longitude - first_longitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_lat) * cos(second_lat) * sin(longitude_delta / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * asin(min(1.0, sqrt(haversine)))


def calculate_location_similarity(distance_meters: float) -> float:
    """Map distance to a centralized civic proximity band."""

    for maximum_distance, similarity in LOCATION_SIMILARITY_BANDS:
        if distance_meters <= maximum_distance:
            return similarity
    return 0.0


def _normalized_label(value: str) -> str:
    return " ".join(value.casefold().split())


def _candidate_labels(
    candidate: MasterIssueCandidate,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    """Use backend labels when present and infer only missing labels locally."""

    inferred = classify_complaint(candidate.description)
    category = candidate.category
    issue = candidate.issue
    notes: list[str] = []

    if category is None and inferred.category != "Other":
        category = inferred.category
        notes.append(f"Candidate category inferred as {category} from its description.")
    if issue is None and inferred.issue != "Unclassified":
        issue = inferred.issue
        notes.append(f"Candidate issue inferred as {issue} from its description.")
    return category, issue, tuple(notes)


def _compatibility(
    new_classification: ClassificationResult,
    candidate_category: str | None,
    candidate_issue: str | None,
) -> tuple[bool | None, bool | None, float]:
    """Calculate category and issue compatibility with missing-data awareness."""

    category_compatible = (
        None
        if candidate_category is None
        else _normalized_label(new_classification.category)
        == _normalized_label(candidate_category)
    )
    issue_compatible = (
        None
        if candidate_issue is None
        else _normalized_label(new_classification.issue)
        == _normalized_label(candidate_issue)
    )

    if category_compatible is False:
        score = 0.0
    elif category_compatible is True and issue_compatible is True:
        score = 1.0
    elif category_compatible is True and issue_compatible is False:
        score = 0.60
    elif category_compatible is True:
        score = 0.70
    elif issue_compatible is True:
        score = 0.80
    else:
        score = 0.0
    return category_compatible, issue_compatible, score


def _location_evidence(
    new_report: ComplaintInput,
    candidate: MasterIssueCandidate,
) -> tuple[float | None, float | None]:
    coordinates = (
        new_report.latitude,
        new_report.longitude,
        candidate.latitude,
        candidate.longitude,
    )
    if any(coordinate is None for coordinate in coordinates):
        return None, None

    distance = haversine_distance_meters(
        new_report.latitude,
        new_report.longitude,
        candidate.latitude,
        candidate.longitude,
    )
    return distance, calculate_location_similarity(distance)


def calculate_fusion_score(
    text_similarity: float,
    location_similarity: float | None,
    compatibility_similarity: float,
    image_similarity: float | None = None,
) -> float:
    """Combine available evidence using centralized deterministic weights."""

    signals: dict[str, float | None] = {
        "text": text_similarity,
        "location": location_similarity,
        "compatibility": compatibility_similarity,
        "image": image_similarity,
    }
    weights = (
        FUSION_WEIGHTS_WITH_IMAGE if image_similarity is not None else FUSION_WEIGHTS
    )
    score = sum(
        weights[name] * (signals[name] if signals[name] is not None else 0.0)
        for name in weights
    )
    return round(score, 4)


def compare_candidate(
    new_report: ComplaintInput,
    new_classification: ClassificationResult,
    candidate: MasterIssueCandidate,
) -> CandidateSimilarity:
    """Evaluate one candidate without mutating or persisting it."""

    text_similarity = calculate_text_similarity(
        new_report.description, candidate.description
    )
    distance, location_similarity = _location_evidence(new_report, candidate)
    candidate_category, candidate_issue, label_notes = _candidate_labels(candidate)
    category_compatible, issue_compatible, compatibility_score = _compatibility(
        new_classification, candidate_category, candidate_issue
    )
    fusion_score = calculate_fusion_score(
        text_similarity,
        location_similarity,
        compatibility_score,
    )

    reasons = [
        f"Deterministic text similarity: {text_similarity:.2f}.",
        *label_notes,
    ]
    if distance is None:
        reasons.append("Geographic evidence unavailable because coordinates are missing.")
    else:
        reasons.append(f"Reports are {distance:.1f} meters apart.")

    if category_compatible is True and issue_compatible is True:
        reasons.append(
            f"Both reports describe {new_classification.category} / "
            f"{new_classification.issue}."
        )
    elif category_compatible is False:
        reasons.append(
            f"Categories are incompatible: {new_classification.category} vs "
            f"{candidate_category}."
        )
    elif category_compatible is True:
        reasons.append(
            "Categories are compatible, but the specific issue labels differ or are unavailable."
        )
    else:
        reasons.append("Category compatibility is unavailable.")

    reasons.append("Image similarity unavailable in the current phase.")
    reasons.append(f"Combined deterministic fusion score: {fusion_score:.2f}.")
    if distance is not None and distance > MAX_DUPLICATE_DISTANCE_METERS:
        reasons.append("Reports are beyond the configured duplicate distance range.")
    if category_compatible is False:
        reasons.append("Incompatible categories prevent Civic Issue Fusion.")

    return CandidateSimilarity(
        issue_id=candidate.issue_id,
        text_similarity=text_similarity,
        location_similarity=location_similarity,
        distance_meters=round(distance, 2) if distance is not None else None,
        category_compatible=category_compatible,
        issue_compatible=issue_compatible,
        image_similarity=None,
        fusion_score=fusion_score,
        reasons=reasons,
    )


def candidate_meets_duplicate_rules(candidate: CandidateSimilarity) -> bool:
    """Apply score and hard compatibility/distance safety gates."""

    if candidate.category_compatible is False:
        return False
    if (
        candidate.distance_meters is not None
        and candidate.distance_meters > MAX_DUPLICATE_DISTANCE_METERS
    ):
        return False
    return candidate.fusion_score >= DUPLICATE_THRESHOLD
