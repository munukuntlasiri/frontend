"""Tests for the deterministic Phase 2 complaint analysis pipeline."""

import unittest

from app.models.schemas import ComplaintInput
from app.services.ai_service import analyze_complaint


class AnalyzeComplaintTests(unittest.TestCase):
    """Verify supported issue classification, priority, and routing."""

    def analyze(self, description: str, citizen_count: int = 1):
        complaint = ComplaintInput(
            description=description,
            citizen_count=citizen_count,
        )
        return analyze_complaint(complaint)

    def test_dangerous_pothole_on_main_road(self) -> None:
        result = self.analyze(
            "There is a huge pothole on the main road and vehicles may meet "
            "with an accident."
        )

        self.assertEqual(result.category, "Road Damage")
        self.assertEqual(result.issue, "Pothole")
        self.assertEqual(result.severity, "High")
        self.assertEqual(result.priority, "High")
        self.assertEqual(result.department, "Road Maintenance Department")

    def test_dumped_garbage(self) -> None:
        result = self.analyze(
            "Garbage has been dumped near our colony for several days."
        )

        self.assertEqual(result.category, "Waste Management")
        self.assertEqual(result.issue, "Garbage Accumulation")
        self.assertEqual(
            result.department, "Sanitation / Waste Management Department"
        )

    def test_overflowing_drain_near_school(self) -> None:
        result = self.analyze(
            "The drainage is blocked and sewage is overflowing near the school."
        )

        self.assertEqual(result.category, "Drainage")
        self.assertEqual(result.issue, "Blocked/Overflowing Drain")
        self.assertEqual(result.severity, "High")
        self.assertIn(result.priority, {"High", "Critical"})
        self.assertEqual(result.department, "Drainage / Sewerage Department")

    def test_non_working_streetlight(self) -> None:
        result = self.analyze(
            "Street light is not working and the road becomes dark at night."
        )

        self.assertEqual(result.category, "Streetlight")
        self.assertEqual(result.issue, "Streetlight Failure")
        self.assertEqual(
            result.department, "Electrical / Street Lighting Department"
        )

    def test_leaking_water_pipe(self) -> None:
        result = self.analyze("A water pipe is leaking continuously.")

        self.assertEqual(result.category, "Water Supply")
        self.assertEqual(result.issue, "Water Leakage")
        self.assertEqual(result.department, "Water Supply Department")

    def test_general_road_damage(self) -> None:
        result = self.analyze("The cracked road near our colony needs repairs.")

        self.assertEqual(result.category, "Road Damage")
        self.assertEqual(result.issue, "General Road Damage")
        self.assertEqual(result.department, "Road Maintenance Department")

    def test_unsupported_complaint(self) -> None:
        result = self.analyze("Please add more benches to the community park.")

        self.assertEqual(result.category, "Other")
        self.assertEqual(result.issue, "Unclassified")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.department, "Civic Services Review Desk")
        self.assertIsNone(result.duplicate_probability)


if __name__ == "__main__":
    unittest.main()
