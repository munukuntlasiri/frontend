"""Recommend deterministic follow-up actions for one issue-state snapshot."""

from datetime import datetime, timezone

from app.models.schemas import (
    FollowUpAction,
    FollowUpDecision,
    FollowUpRequest,
    FollowUpUrgency,
)

# Prototype demo SLAs, not official municipal service-level commitments.
PROTOTYPE_SLA_HOURS: dict[str, float] = {
    "Critical": 2.0,
    "High": 6.0,
    "Medium": 24.0,
    "Low": 48.0,
}

REMINDER_GRACE_HOURS: dict[str, float] = {
    "Critical": 1.0,
    "High": 2.0,
    "Medium": 8.0,
    "Low": 12.0,
}

ESCALATION_GRACE_HOURS: dict[str, float] = {
    "Critical": 2.0,
    "High": 4.0,
    "Medium": 12.0,
    "Low": 24.0,
}

RECENT_UPDATE_GRACE_HOURS: dict[str, float] = {
    "Critical": 1.0,
    "High": 3.0,
    "Medium": 8.0,
    "Low": 12.0,
}

# Recent updates defer action only until total assignment age reaches this SLA multiple.
MAX_RECENT_UPDATE_PROTECTION_MULTIPLIER = 3.0

STOP_STATUSES = frozenset(
    {
        "resolved",
        "closed",
        "rejected",
        "invalid",
        "rejected invalid",
        "cancelled",
        "canceled",
    }
)


def _normalized_status(status: str) -> str:
    return " ".join(status.casefold().replace("/", " ").replace("_", " ").split())


def _hours_between(earlier: datetime, later: datetime) -> float:
    return (later - earlier).total_seconds() / 3600.0


def _rounded_hours(value: float) -> float:
    return round(max(0.0, value), 2)


def _decision(
    request: FollowUpRequest,
    action: FollowUpAction,
    urgency: FollowUpUrgency,
    should_notify: bool,
    target: str | None,
    assignment_hours: float | None,
    update_hours: float | None,
    reasons: list[str],
    next_check_hours: float | None,
) -> FollowUpDecision:
    reasons.append(f"Recommended action: {action.value}.")
    return FollowUpDecision(
        issue_id=request.issue_id,
        action=action,
        urgency=urgency,
        should_notify=should_notify,
        target=target,
        hours_since_assignment=(
            _rounded_hours(assignment_hours) if assignment_hours is not None else None
        ),
        hours_since_last_update=(
            _rounded_hours(update_hours) if update_hours is not None else None
        ),
        reasons=reasons,
        next_check_hours=(
            _rounded_hours(next_check_hours) if next_check_hours is not None else None
        ),
    )


def evaluate_follow_up(request: FollowUpRequest) -> FollowUpDecision:
    """Evaluate one snapshot without scheduling, persistence, or notification delivery."""

    now = request.now or datetime.now(timezone.utc)
    status = _normalized_status(request.status)
    if status in STOP_STATUSES:
        return _decision(
            request=request,
            action=FollowUpAction.STOP_FOLLOWUP,
            urgency=FollowUpUrgency.NONE,
            should_notify=False,
            target=None,
            assignment_hours=None,
            update_hours=None,
            reasons=[f"Issue status {request.status!r} ends active follow-up."],
            next_check_hours=None,
        )

    if request.assigned_at is None:
        return _decision(
            request=request,
            action=FollowUpAction.NO_ACTION,
            urgency=FollowUpUrgency.UNKNOWN,
            should_notify=False,
            target=None,
            assignment_hours=None,
            update_hours=None,
            reasons=[
                "Assignment time is unavailable, so elapsed-time SLA evaluation "
                "cannot be performed.",
                "The backend should supply assigned_at in a later snapshot.",
            ],
            next_check_hours=None,
        )

    assignment_hours = _hours_between(request.assigned_at, now)
    if assignment_hours < 0:
        raise ValueError("assigned_at cannot be later than the evaluation time")
    update_hours = (
        _hours_between(request.last_updated_at, now)
        if request.last_updated_at is not None
        else None
    )
    if update_hours is not None and update_hours < 0:
        raise ValueError("last_updated_at cannot be later than the evaluation time")

    priority = request.priority
    sla_hours = PROTOTYPE_SLA_HOURS[priority]
    reasons = [
        f"{priority}-priority prototype SLA is {sla_hours:g} hours.",
        f"Issue has been assigned for {assignment_hours:.1f} hours.",
    ]
    if update_hours is None:
        reasons.append(
            f"No meaningful update has been recorded during the "
            f"{assignment_hours:.1f} assignment hours."
        )
    else:
        reasons.append(f"A meaningful update occurred {update_hours:.1f} hours ago.")

    if assignment_hours <= sla_hours:
        reasons.append("Issue remains within the prototype initial-response SLA.")
        return _decision(
            request,
            FollowUpAction.NO_ACTION,
            FollowUpUrgency.LOW,
            False,
            None,
            assignment_hours,
            update_hours,
            reasons,
            sla_hours - assignment_hours,
        )

    reasons.append("Initial response SLA has been exceeded.")
    recent_update_grace = RECENT_UPDATE_GRACE_HOURS[priority]
    maximum_protected_age = sla_hours * MAX_RECENT_UPDATE_PROTECTION_MULTIPLIER
    if (
        update_hours is not None
        and update_hours <= recent_update_grace
        and assignment_hours <= maximum_protected_age
    ):
        reasons.extend(
            [
                f"Recent activity is within the {recent_update_grace:g}-hour "
                "follow-up grace window.",
                f"Recent updates can defer action only until assignment age reaches "
                f"{maximum_protected_age:g} hours.",
            ]
        )
        return _decision(
            request,
            FollowUpAction.NO_ACTION,
            FollowUpUrgency.LOW,
            False,
            None,
            assignment_hours,
            update_hours,
            reasons,
            min(
                recent_update_grace - update_hours,
                maximum_protected_age - assignment_hours,
            ),
        )

    if request.reminder_count == 0:
        reasons.append("No reminder has previously been issued.")
        return _decision(
            request,
            FollowUpAction.REMINDER,
            FollowUpUrgency.MEDIUM,
            True,
            request.department or "Assigned department",
            assignment_hours,
            update_hours,
            reasons,
            REMINDER_GRACE_HOURS[priority],
        )

    escalation_checkpoint = sla_hours + REMINDER_GRACE_HOURS[priority]
    if request.escalation_count == 0 and assignment_hours < escalation_checkpoint:
        reasons.append(
            f"A reminder exists; escalation checkpoint is {escalation_checkpoint:g} "
            "hours after assignment."
        )
        return _decision(
            request,
            FollowUpAction.NO_ACTION,
            FollowUpUrgency.MEDIUM,
            False,
            None,
            assignment_hours,
            update_hours,
            reasons,
            escalation_checkpoint - assignment_hours,
        )

    if request.escalation_count == 0:
        reasons.append(
            f"Reminder grace period of {REMINDER_GRACE_HOURS[priority]:g} hours "
            "has elapsed without a recent meaningful update."
        )
        return _decision(
            request,
            FollowUpAction.ESCALATE,
            FollowUpUrgency.HIGH,
            True,
            "Department supervisor / escalation queue",
            assignment_hours,
            update_hours,
            reasons,
            ESCALATION_GRACE_HOURS[priority],
        )

    critical_checkpoint = escalation_checkpoint + ESCALATION_GRACE_HOURS[priority]
    if priority in {"Critical", "High"} and assignment_hours >= critical_checkpoint:
        reasons.append(
            f"Escalation grace period has elapsed; critical checkpoint was "
            f"{critical_checkpoint:g} assignment hours."
        )
        return _decision(
            request,
            FollowUpAction.CRITICAL_ESCALATION,
            FollowUpUrgency.CRITICAL,
            True,
            "Senior civic authority / emergency escalation queue",
            assignment_hours,
            update_hours,
            reasons,
            ESCALATION_GRACE_HOURS[priority],
        )

    if assignment_hours < critical_checkpoint:
        reasons.append(
            f"An escalation exists; next checkpoint is {critical_checkpoint:g} "
            "hours after assignment."
        )
        return _decision(
            request,
            FollowUpAction.NO_ACTION,
            FollowUpUrgency.HIGH,
            False,
            None,
            assignment_hours,
            update_hours,
            reasons,
            critical_checkpoint - assignment_hours,
        )

    reasons.append("Continued delay remains beyond the escalation grace period.")
    return _decision(
        request,
        FollowUpAction.ESCALATE,
        FollowUpUrgency.HIGH,
        True,
        "Department supervisor / escalation queue",
        assignment_hours,
        update_hours,
        reasons,
        ESCALATION_GRACE_HOURS[priority],
    )
