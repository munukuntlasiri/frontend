"""Orchestrate CivicResolve AI agents behind one service interface."""

from app.agents.complaint_agent import classify_complaint
from app.agents.fusion_agent import (
    DUPLICATE_THRESHOLD,
    candidate_meets_duplicate_rules,
    compare_candidate,
)
from app.agents.followup_agent import evaluate_follow_up
from app.agents.priority_agent import calculate_priority
from app.agents.routing_agent import route_department
from app.models.schemas import (
    ComplaintAnalysis,
    ComplaintInput,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    FollowUpDecision,
    FollowUpRequest,
)


def analyze_complaint(complaint: ComplaintInput) -> ComplaintAnalysis:
    """Run the local Phase 2 complaint intelligence pipeline."""

    classification = classify_complaint(complaint.description)
    priority = calculate_priority(complaint, classification)
    department = route_department(classification.category)

    return ComplaintAnalysis(
        category=classification.category,
        issue=classification.issue,
        severity=classification.severity,
        confidence=classification.confidence,
        confidence_basis="deterministic_rule_match",
        risk=classification.risk,
        priority=priority.priority,
        priority_score=priority.score,
        department=department,
        duplicate_probability=None,
        classification_reasons=list(classification.reasons),
        priority_reasons=list(priority.reasons),
    )


def check_duplicate_candidates(request: DuplicateCheckRequest) -> DuplicateCheckResponse:
    """Compare a new report with backend-supplied Master Issue candidates."""

    if not request.candidates:
        return DuplicateCheckResponse(
            is_duplicate=False,
            duplicate_probability=0.0,
            matched_issue_id=None,
            best_match=None,
            candidate_results=[],
            evaluated_candidates=0,
            decision_reasons=(
                "No candidate Master Civic Issues were supplied; create a new issue.",
            ),
        )

    classification = classify_complaint(request.new_report.description)
    results = [
        compare_candidate(request.new_report, classification, candidate)
        for candidate in request.candidates
    ]
    valid_matches = [result for result in results if candidate_meets_duplicate_rules(result)]
    if valid_matches:
        best_match = max(valid_matches, key=lambda result: result.fusion_score)
        is_duplicate = True
    else:
        best_match = max(results, key=lambda result: result.fusion_score)
        is_duplicate = False

    decision_reasons = [
        f"Best candidate {best_match.issue_id} has deterministic fusion score "
        f"{best_match.fusion_score:.2f}."
    ]
    if is_duplicate:
        decision_reasons.append(
            f"Score meets the duplicate threshold of {DUPLICATE_THRESHOLD:.2f}, "
            "and compatibility and distance gates passed."
        )
    else:
        decision_reasons.append(
            f"No candidate met all fusion rules and the duplicate threshold of "
            f"{DUPLICATE_THRESHOLD:.2f}; treat this as a new Master Civic Issue."
        )

    return DuplicateCheckResponse(
        is_duplicate=is_duplicate,
        duplicate_probability=best_match.fusion_score,
        matched_issue_id=best_match.issue_id if is_duplicate else None,
        best_match=best_match,
        candidate_results=results,
        evaluated_candidates=len(results),
        decision_reasons=decision_reasons,
    )


def evaluate_issue_follow_up(request: FollowUpRequest) -> FollowUpDecision:
    """Return the follow-up recommendation for one backend-supplied snapshot."""

    return evaluate_follow_up(request)
