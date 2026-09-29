"""Tests for deterministic Civic Issue Fusion and duplicate detection."""

import unittest

from app.models.schemas import (
    ComplaintInput,
    DuplicateCheckRequest,
    MasterIssueCandidate,
)
from app.services.ai_service import check_duplicate_candidates


class DuplicateCheckTests(unittest.TestCase):
    """Verify fusion behavior across text, location, and issue signals."""

    def check(
        self,
        description: str,
        candidates: list[MasterIssueCandidate],
        latitude: float | None = 17.3850,
        longitude: float | None = 78.4867,
    ):
        request = DuplicateCheckRequest(
            new_report=ComplaintInput(
                description=description,
                latitude=latitude,
                longitude=longitude,
            ),
            candidates=candidates,
        )
        return check_duplicate_candidates(request)

    @staticmethod
    def candidate(
        issue_id: str,
        description: str,
        category: str,
        issue: str,
        latitude: float | None,
        longitude: float | None,
    ) -> MasterIssueCandidate:
        return MasterIssueCandidate(
            issue_id=issue_id,
            description=description,
            category=category,
            issue=issue,
            latitude=latitude,
            longitude=longitude,
            status="Open",
        )

    def test_same_nearby_pothole_is_duplicate(self) -> None:
        candidate = self.candidate(
            "MI-1024",
            "Large hole in road causing problems.",
            "Road Damage",
            "Pothole",
            17.3852,
            78.4867,
        )

        result = self.check(
            "There is a huge pothole on the main road.", [candidate]
        )

        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.matched_issue_id, "MI-1024")
        self.assertGreaterEqual(result.duplicate_probability, 0.72)

    def test_similar_pothole_far_away_is_not_duplicate(self) -> None:
        candidate = self.candidate(
            "MI-FAR",
            "Huge pothole on the main road.",
            "Road Damage",
            "Pothole",
            17.4500,
            78.4867,
        )

        result = self.check("Huge pothole on the main road.", [candidate])

        self.assertFalse(result.is_duplicate)
        self.assertIsNone(result.matched_issue_id)
        self.assertGreater(result.best_match.distance_meters, 100.0)

    def test_same_location_different_issue_is_not_duplicate(self) -> None:
        candidate = self.candidate(
            "MI-POTHOLE",
            "Large pothole on the road.",
            "Road Damage",
            "Pothole",
            17.3850,
            78.4867,
        )

        result = self.check("Garbage dumped beside the road.", [candidate])

        self.assertFalse(result.is_duplicate)
        self.assertFalse(result.best_match.category_compatible)

    def test_paraphrased_nearby_streetlight_is_duplicate(self) -> None:
        candidate = self.candidate(
            "MI-LIGHT",
            "The streetlamp on this road has stopped working.",
            "Streetlight",
            "Streetlight Failure",
            17.3851,
            78.4867,
        )

        result = self.check("Street light is not working.", [candidate])

        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.matched_issue_id, "MI-LIGHT")

    def test_best_of_multiple_candidates_is_nearby_pothole(self) -> None:
        candidates = [
            self.candidate(
                "MI-NEAR",
                "Large hole in road causing problems.",
                "Road Damage",
                "Pothole",
                17.3851,
                78.4867,
            ),
            self.candidate(
                "MI-FAR",
                "Huge pothole on the main road.",
                "Road Damage",
                "Pothole",
                17.4500,
                78.4867,
            ),
            self.candidate(
                "MI-GARBAGE",
                "Garbage has been dumped beside the road.",
                "Waste Management",
                "Garbage Accumulation",
                17.3850,
                78.4867,
            ),
        ]

        result = self.check("There is a huge pothole on the main road.", candidates)

        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.matched_issue_id, "MI-NEAR")
        self.assertEqual(result.evaluated_candidates, 3)
        self.assertEqual(len(result.candidate_results), 3)

    def test_no_candidates_returns_new_issue_decision(self) -> None:
        result = self.check("A pothole is blocking the road.", [])

        self.assertFalse(result.is_duplicate)
        self.assertIsNone(result.matched_issue_id)
        self.assertIsNone(result.best_match)
        self.assertEqual(result.evaluated_candidates, 0)

    def test_missing_location_is_explicit_and_conservative(self) -> None:
        candidate = self.candidate(
            "MI-NO-LOCATION",
            "Large pothole on the road.",
            "Road Damage",
            "Pothole",
            None,
            None,
        )

        result = self.check(
            "Large pothole on the road.",
            [candidate],
            latitude=None,
            longitude=None,
        )

        self.assertFalse(result.is_duplicate)
        self.assertIsNone(result.best_match.distance_meters)
        self.assertIsNone(result.best_match.location_similarity)
        self.assertTrue(
            any("Geographic evidence unavailable" in reason for reason in result.best_match.reasons)
        )


if __name__ == "__main__":
    unittest.main()
