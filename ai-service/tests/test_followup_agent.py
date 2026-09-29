"""Tests for deterministic follow-up and escalation recommendations."""

from datetime import datetime, timedelta, timezone
import unittest

from pydantic import ValidationError

from app.agents.followup_agent import evaluate_follow_up
from app.models.schemas import FollowUpAction, FollowUpRequest

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


def request(**overrides) -> FollowUpRequest:
    values = {
        "issue_id": "MI-100",
        "status": "Assigned",
        "priority": "High",
        "assigned_at": NOW - timedelta(hours=2),
        "department": "Road Maintenance Department",
        "now": NOW,
    }
    values.update(overrides)
    return FollowUpRequest(**values)


class FollowUpAgentTests(unittest.TestCase):
    """Verify SLA, activity, lifecycle, and counter-based decisions."""

    def test_high_priority_within_sla(self) -> None:
        decision = evaluate_follow_up(request())

        self.assertEqual(decision.action, FollowUpAction.NO_ACTION)
        self.assertEqual(decision.next_check_hours, 4.0)

    def test_high_priority_overdue_requires_reminder(self) -> None:
        decision = evaluate_follow_up(
            request(assigned_at=NOW - timedelta(hours=8))
        )

        self.assertEqual(decision.action, FollowUpAction.REMINDER)
        self.assertTrue(decision.should_notify)
        self.assertEqual(decision.target, "Road Maintenance Department")

    def test_high_priority_after_reminder_requires_escalation(self) -> None:
        decision = evaluate_follow_up(
            request(
                assigned_at=NOW - timedelta(hours=10),
                reminder_count=1,
            )
        )

        self.assertEqual(decision.action, FollowUpAction.ESCALATE)
        self.assertIn("supervisor", decision.target.casefold())

    def test_critical_substantial_delay_requires_critical_escalation(self) -> None:
        decision = evaluate_follow_up(
            request(
                priority="Critical",
                assigned_at=NOW - timedelta(hours=8),
                reminder_count=1,
                escalation_count=1,
            )
        )

        self.assertEqual(decision.action, FollowUpAction.CRITICAL_ESCALATION)
        self.assertTrue(decision.should_notify)

    def test_recent_medium_priority_update_uses_grace_window(self) -> None:
        decision = evaluate_follow_up(
            request(
                priority="Medium",
                assigned_at=NOW - timedelta(hours=30),
                last_updated_at=NOW - timedelta(hours=1),
            )
        )

        self.assertEqual(decision.action, FollowUpAction.NO_ACTION)
        self.assertEqual(decision.hours_since_last_update, 1.0)
        self.assertGreater(decision.next_check_hours, 0.0)

    def test_resolved_issue_stops_follow_up(self) -> None:
        decision = evaluate_follow_up(request(status="Resolved"))

        self.assertEqual(decision.action, FollowUpAction.STOP_FOLLOWUP)
        self.assertFalse(decision.should_notify)
        self.assertIsNone(decision.next_check_hours)

    def test_closed_issue_stops_follow_up(self) -> None:
        decision = evaluate_follow_up(request(status="Closed"))

        self.assertEqual(decision.action, FollowUpAction.STOP_FOLLOWUP)

    def test_missing_assignment_time_is_safe_and_explainable(self) -> None:
        decision = evaluate_follow_up(request(assigned_at=None))

        self.assertEqual(decision.action, FollowUpAction.NO_ACTION)
        self.assertIsNone(decision.hours_since_assignment)
        self.assertTrue(any("unavailable" in reason for reason in decision.reasons))

    def test_negative_counters_fail_validation(self) -> None:
        with self.assertRaises(ValidationError):
            request(reminder_count=-1)
        with self.assertRaises(ValidationError):
            request(escalation_count=-1)

    def test_timezone_aware_offsets_are_calculated_correctly(self) -> None:
        india_timezone = timezone(timedelta(hours=5, minutes=30))
        assigned_in_india = (NOW - timedelta(hours=8)).astimezone(india_timezone)

        decision = evaluate_follow_up(request(assigned_at=assigned_in_india))

        self.assertEqual(decision.hours_since_assignment, 8.0)
        self.assertEqual(decision.action, FollowUpAction.REMINDER)

    def test_naive_datetime_fails_validation(self) -> None:
        with self.assertRaises(ValidationError):
            request(assigned_at=datetime(2026, 1, 15, 10, 0))


if __name__ == "__main__":
    unittest.main()
