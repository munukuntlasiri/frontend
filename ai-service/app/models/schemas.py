"""Shared schemas for AI service contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class ComplaintInput(BaseModel):
    """Citizen complaint data submitted for AI analysis."""

    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=5_000)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    citizen_count: int = Field(default=1, ge=1)


class ComplaintAnalysis(BaseModel):
    """Structured result produced from a citizen complaint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic rule-match confidence, not an ML probability.",
    )
    confidence_basis: str = Field(
        default="deterministic_rule_match",
        description="Method used to calculate the confidence value.",
    )
    risk: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    priority_score: int = Field(ge=0, le=100)
    department: str = Field(min_length=1)
    duplicate_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Null until Civic Issue Fusion is implemented.",
    )
    classification_reasons: list[str] = Field(default_factory=list)
    priority_reasons: list[str] = Field(default_factory=list)


class MasterIssueCandidate(BaseModel):
    """Existing Master Civic Issue supplied by the backend for comparison."""

    model_config = ConfigDict(str_strip_whitespace=True)

    issue_id: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5_000)
    category: str | None = Field(default=None, min_length=1)
    issue: str | None = Field(default=None, min_length=1)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    status: str | None = Field(default=None, min_length=1)


class DuplicateCheckRequest(BaseModel):
    """New report and backend-selected Master Issue candidates."""

    new_report: ComplaintInput
    candidates: list[MasterIssueCandidate]


class CandidateSimilarity(BaseModel):
    """Explainable deterministic comparison against one candidate issue."""

    issue_id: str
    text_similarity: float = Field(ge=0.0, le=1.0)
    location_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    distance_meters: float | None = Field(default=None, ge=0.0)
    category_compatible: bool | None
    issue_compatible: bool | None
    image_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    fusion_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic MVP fusion score, not an ML probability.",
    )
    reasons: list[str] = Field(default_factory=list)


class DuplicateCheckResponse(BaseModel):
    """Best duplicate decision and all evaluated candidate comparisons."""

    is_duplicate: bool
    duplicate_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Best deterministic fusion score, not a calibrated probability.",
    )
    matched_issue_id: str | None
    best_match: CandidateSimilarity | None
    candidate_results: list[CandidateSimilarity] = Field(default_factory=list)
    evaluated_candidates: int = Field(ge=0)
    decision_reasons: list[str] = Field(default_factory=list)


class VisionPrediction(BaseModel):
    """One ranked whole-image civic prompt-group result."""

    category: str = Field(min_length=1)
    issue: str | None = None
    taxonomy_category: str = Field(min_length=1)
    taxonomy_issue: str | None = None
    relative_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relative zero-shot prompt score, not a calibrated probability.",
    )
    top_prompt: str = Field(min_length=1)


class VisionAnalysis(BaseModel):
    """Structured result from local whole-image vision inference."""

    detected: bool
    category: str | None
    issue: str | None
    taxonomy_category: str | None
    taxonomy_issue: str | None
    relative_score: float | None = Field(default=None, ge=0.0, le=1.0)
    score_type: str = "relative_zero_shot_prompt_score"
    provider: str
    model: str
    device: str
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    predictions: list[VisionPrediction] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ResolutionDecision(StrEnum):
    """Conservative result of comparing before and after issue evidence."""

    VERIFIED = "VERIFIED"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    UNCERTAIN = "UNCERTAIN"


class ResolutionAction(StrEnum):
    """Backend action recommended after resolution verification."""

    REQUEST_CITIZEN_CONFIRMATION = "REQUEST_CITIZEN_CONFIRMATION"
    KEEP_OPEN = "KEEP_OPEN"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ResolutionEvidence(BaseModel):
    """Target-specific evidence extracted from one submitted image."""

    category: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    taxonomy_category: str = Field(min_length=1)
    taxonomy_issue: str = Field(min_length=1)
    relative_score: float = Field(ge=0.0, le=1.0)
    detected: bool
    top_prompt: str = Field(min_length=1)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)


class ResolutionVerification(BaseModel):
    """Explainable, non-closing recommendation from before/after evidence."""

    issue_id: str | None = None
    decision: ResolutionDecision
    verification_score: float | None = Field(default=None, ge=0.0, le=1.0)
    score_type: str = "relative_target_score_reduction_not_probability"
    before_evidence: ResolutionEvidence
    after_evidence: ResolutionEvidence
    issue_score_before: float = Field(ge=0.0, le=1.0)
    issue_score_after: float = Field(ge=0.0, le=1.0)
    score_reduction: float = Field(ge=-1.0, le=1.0)
    score_reduction_ratio: float | None = Field(default=None, le=1.0)
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    requires_human_review: bool
    recommended_action: ResolutionAction


class FollowUpAction(StrEnum):
    """Actions the backend may take after a follow-up evaluation."""

    NO_ACTION = "NO_ACTION"
    REMINDER = "REMINDER"
    ESCALATE = "ESCALATE"
    CRITICAL_ESCALATION = "CRITICAL_ESCALATION"
    STOP_FOLLOWUP = "STOP_FOLLOWUP"


class FollowUpUrgency(StrEnum):
    """Urgency attached to a recommended follow-up action."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class FollowUpRequest(BaseModel):
    """Current issue snapshot supplied by the backend or its scheduler."""

    model_config = ConfigDict(str_strip_whitespace=True)

    issue_id: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=100)
    priority: str = Field(min_length=1, max_length=20)
    assigned_at: AwareDatetime | None = None
    last_updated_at: AwareDatetime | None = None
    reminder_count: int = Field(default=0, ge=0)
    escalation_count: int = Field(default=0, ge=0)
    department: str | None = Field(default=None, min_length=1, max_length=200)
    citizen_count: int = Field(default=1, ge=1)
    severity: str | None = Field(default=None, min_length=1, max_length=50)
    risk: str | None = Field(default=None, min_length=1, max_length=200)
    now: AwareDatetime | None = None

    @field_validator("priority")
    @classmethod
    def normalize_priority(cls, value: str) -> str:
        priorities = {
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        normalized = priorities.get(value.casefold())
        if normalized is None:
            raise ValueError("priority must be Critical, High, Medium, or Low")
        return normalized

    @model_validator(mode="after")
    def validate_lifecycle_order(self) -> "FollowUpRequest":
        if (
            self.assigned_at is not None
            and self.last_updated_at is not None
            and self.last_updated_at < self.assigned_at
        ):
            raise ValueError("last_updated_at cannot be earlier than assigned_at")
        if self.now is not None:
            if self.assigned_at is not None and self.assigned_at > self.now:
                raise ValueError("assigned_at cannot be later than now")
            if self.last_updated_at is not None and self.last_updated_at > self.now:
                raise ValueError("last_updated_at cannot be later than now")
        return self


class FollowUpDecision(BaseModel):
    """Explainable action recommendation for one current issue snapshot."""

    issue_id: str
    action: FollowUpAction
    urgency: FollowUpUrgency
    should_notify: bool
    target: str | None
    hours_since_assignment: float | None = Field(default=None, ge=0.0)
    hours_since_last_update: float | None = Field(default=None, ge=0.0)
    reasons: list[str] = Field(default_factory=list)
    next_check_hours: float | None = Field(default=None, ge=0.0)


class HealthResponse(BaseModel):
    """Health information returned by the service."""

    status: str
    service: str
    version: str
