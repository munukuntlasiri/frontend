"""Tests for vision validation, rejection, and the multipart API boundary."""

from io import BytesIO
import unittest

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.agents.vision_agent import (
    MAX_UPLOAD_BYTES,
    MIN_CIVIC_RELATIVE_SCORE,
    MIN_CONTROL_MARGIN,
    MIN_RUNNER_UP_MARGIN,
    VISION_CATEGORIES,
    VisionAgent,
)
from app.main import app, classify_image


class FakeVisionProvider:
    """Predictable provider that never loads a real model."""

    provider_name = "fake_test_provider"
    model_id = "fake-test-model"
    device = "cpu"

    def __init__(self, scores_by_prompt: dict[str, float]) -> None:
        self.scores_by_prompt = scores_by_prompt
        self.calls = 0

    def score_prompts(self, image, prompts) -> list[float]:
        self.calls += 1
        return [self.scores_by_prompt.get(prompt, 0.01) for prompt in prompts]


def image_bytes(image_format: str) -> bytes:
    """Create a small real image encoding for validation-only unit tests."""

    output = BytesIO()
    Image.new("RGB", (16, 12), color=(80, 90, 100)).save(
        output, format=image_format
    )
    return output.getvalue()


def png_bytes() -> bytes:
    return image_bytes("PNG")


def detected_provider() -> FakeVisionProvider:
    pothole_prompts = VISION_CATEGORIES[0].prompts
    return FakeVisionProvider({prompt: 0.45 for prompt in pothole_prompts})


def rejected_provider() -> FakeVisionProvider:
    control_prompts = VISION_CATEGORIES[-1].prompts
    return FakeVisionProvider({prompt: 0.08 for prompt in control_prompts})


class VisionAgentTests(unittest.TestCase):
    """Test provider-independent classification and rejection behavior."""

    def test_detected_civic_issue(self) -> None:
        provider = detected_provider()
        result = VisionAgent(provider).analyze(png_bytes(), "image/png")

        self.assertTrue(result.detected)
        self.assertEqual(result.category, "Road Damage")
        self.assertEqual(result.issue, "Pothole")
        self.assertEqual(result.score_type, "relative_zero_shot_prompt_score")
        self.assertEqual(provider.calls, 1)

    def test_rejected_no_civic_issue(self) -> None:
        result = VisionAgent(rejected_provider()).analyze(
            png_bytes(), "image/png"
        )

        self.assertFalse(result.detected)
        self.assertIsNone(result.category)
        self.assertIsNone(result.issue)
        self.assertIsNone(result.relative_score)
        self.assertGreater(len(result.predictions), 0)


class VisionTaxonomyTests(unittest.TestCase):
    """Verify taxonomy coverage and conservative provider-driven selection."""

    REQUIRED_HIERARCHY = {
        "Road": {
            "Pothole",
            "Cracked Road",
            "Damaged Pavement",
            "Broken Footpath",
        },
        "Waste Management": {
            "Garbage Accumulation",
            "Overflowing Bin",
            "Illegal Dumping",
        },
        "Water": {
            "Water Leakage",
            "Drainage Overflow",
            "Waterlogging",
            "Open Drain",
        },
        "Infrastructure": {
            "Broken Streetlight",
            "Damaged Public Infrastructure",
            "Broken Traffic-related Infrastructure",
        },
    }

    @staticmethod
    def prompts_for(issue: str) -> tuple[str, ...]:
        return next(
            config.prompts
            for config in VISION_CATEGORIES
            if config.taxonomy_issue == issue
        )

    def test_all_fourteen_required_issues_are_represented(self) -> None:
        actual = {
            category: {
                config.taxonomy_issue
                for config in VISION_CATEGORIES
                if not config.is_control and config.taxonomy_category == category
            }
            for category in self.REQUIRED_HIERARCHY
        }

        self.assertEqual(actual, self.REQUIRED_HIERARCHY)
        self.assertEqual(sum(len(issues) for issues in actual.values()), 14)

    def test_existing_five_compatibility_labels_remain_represented(self) -> None:
        labels = {
            (config.category, config.issue)
            for config in VISION_CATEGORIES
            if not config.is_control
        }

        self.assertTrue(
            {
                ("Road Damage", "Pothole"),
                ("Waste Management", "Garbage Accumulation"),
                ("Water Supply", "Water Leakage"),
                ("Drainage", "Drainage Problem"),
                ("Streetlight", "Visible Streetlight Damage"),
            }.issubset(labels)
        )
        self.assertTrue(any(config.is_control for config in VISION_CATEGORIES))

    def test_each_issue_has_multiple_prompts_and_only_validated_types_auto_verify(self) -> None:
        civic_configs = [
            config for config in VISION_CATEGORIES if not config.is_control
        ]
        self.assertTrue(all(len(config.prompts) >= 2 for config in civic_configs))
        self.assertEqual(
            {
                config.taxonomy_issue
                for config in civic_configs
                if config.automatic_resolution_supported
            },
            {
                "Pothole",
                "Garbage Accumulation",
                "Water Leakage",
                "Drainage Overflow",
                "Broken Streetlight",
            },
        )

    def test_affected_sibling_prompts_are_distinct_and_observable(self) -> None:
        affected_issues = {
            "Pothole",
            "Cracked Road",
            "Damaged Pavement",
            "Garbage Accumulation",
            "Illegal Dumping",
            "Drainage Overflow",
            "Waterlogging",
            "Open Drain",
        }
        prompt_sets = {
            issue: self.prompts_for(issue) for issue in affected_issues
        }

        self.assertTrue(all(len(prompts) == 3 for prompts in prompt_sets.values()))
        flattened = [prompt for prompts in prompt_sets.values() for prompt in prompts]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertTrue(
            all(
                any(term in prompt for term in ("hole", "cavity"))
                for prompt in prompt_sets["Pothole"]
            )
        )
        self.assertTrue(
            all("crack" in prompt for prompt in prompt_sets["Cracked Road"])
        )
        self.assertTrue(
            all(
                not any(term in prompt for term in ("pothole", "crack", "hole"))
                for prompt in prompt_sets["Damaged Pavement"]
            )
        )
        self.assertTrue(
            all(
                not any(term in prompt for term in ("dump", "overflow", "bin"))
                for prompt in prompt_sets["Garbage Accumulation"]
            )
        )
        self.assertTrue(
            all(
                any(
                    term in prompt
                    for term in (
                        "bulky",
                        "construction",
                        "furniture",
                        "appliances",
                        "debris",
                    )
                )
                for prompt in prompt_sets["Illegal Dumping"]
            )
        )
        self.assertTrue(
            all(
                any(term in prompt for term in ("spilling", "flowing", "overflowing"))
                for prompt in prompt_sets["Drainage Overflow"]
            )
        )
        self.assertTrue(
            all("drain" not in prompt for prompt in prompt_sets["Waterlogging"])
        )
        self.assertTrue(
            all(
                any(term in prompt for term in ("uncovered", "exposed", "open"))
                for prompt in prompt_sets["Open Drain"]
            )
        )

    def test_water_sibling_prompts_encode_different_visible_conditions(self) -> None:
        overflow = self.prompts_for("Drainage Overflow")
        waterlogging = self.prompts_for("Waterlogging")
        open_drain = self.prompts_for("Open Drain")

        self.assertTrue(
            all(
                any(term in prompt for term in ("onto", "beyond"))
                and any(
                    surface in prompt
                    for surface in ("road", "street", "footpath", "public surface")
                )
                for prompt in overflow
            )
        )
        self.assertTrue(
            all(
                any(term in prompt for term in ("broad", "large areas", "covered"))
                for prompt in waterlogging
            )
        )
        self.assertTrue(
            all(
                any(
                    structure in prompt
                    for structure in ("interior", "channel walls")
                )
                for prompt in open_drain
            )
        )
        self.assertTrue(any("contained inside" in prompt for prompt in open_drain))
        self.assertTrue(
            all(
                not any(term in prompt for term in ("overflow", "spilling", "flood"))
                for prompt in open_drain
            )
        )

    def test_global_detection_gates_remain_unchanged(self) -> None:
        self.assertEqual(MIN_CIVIC_RELATIVE_SCORE, 0.20)
        self.assertEqual(MIN_CONTROL_MARGIN, 0.10)
        self.assertEqual(MIN_RUNNER_UP_MARGIN, 0.10)

    def test_new_issue_is_reachable_through_provider_scores(self) -> None:
        cracked = next(
            config
            for config in VISION_CATEGORIES
            if config.taxonomy_issue == "Cracked Road"
        )
        provider = FakeVisionProvider(
            {prompt: 0.45 for prompt in cracked.prompts}
        )

        result = VisionAgent(provider).analyze(png_bytes(), "image/png")

        self.assertTrue(result.detected)
        self.assertEqual(result.category, "Road Damage")
        self.assertEqual(result.issue, "Cracked Road")
        self.assertEqual(result.taxonomy_category, "Road")
        self.assertEqual(result.taxonomy_issue, "Cracked Road")

    def test_similar_high_scoring_issues_are_rejected_as_ambiguous(self) -> None:
        pothole = next(
            config
            for config in VISION_CATEGORIES
            if config.taxonomy_issue == "Pothole"
        )
        cracked = next(
            config
            for config in VISION_CATEGORIES
            if config.taxonomy_issue == "Cracked Road"
        )
        scores = {
            prompt: 0.45 for config in (pothole, cracked) for prompt in config.prompts
        }

        result = VisionAgent(FakeVisionProvider(scores)).analyze(
            png_bytes(), "image/png"
        )

        self.assertFalse(result.detected)
        self.assertIsNone(result.taxonomy_issue)

    def test_all_existing_api_routes_remain_registered(self) -> None:
        paths = {route.path for route in app.routes}
        self.assertTrue(
            {
                "/",
                "/health",
                "/analyze",
                "/duplicate-check",
                "/classify-image",
                "/follow-up",
                "/verify-resolution",
            }.issubset(paths)
        )


class VisionEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Verify multipart endpoint status handling without loading SigLIP."""

    @staticmethod
    def upload(
        data: bytes, content_type: str, filename: str = "evidence"
    ) -> UploadFile:
        return UploadFile(
            file=BytesIO(data),
            filename=filename,
            headers=Headers({"content-type": content_type}),
        )

    async def test_valid_image(self) -> None:
        result = await classify_image(
            self.upload(png_bytes(), "image/png"),
            VisionAgent(detected_provider()),
        )

        self.assertTrue(result.detected)
        self.assertEqual(result.image_width, 16)
        self.assertEqual(result.image_height, 12)

    async def test_genuine_jpeg_png_and_webp_are_accepted(self) -> None:
        cases = (
            ("JPEG", "image/jpeg", "evidence.jpg"),
            ("PNG", "image/png", "evidence.png"),
            ("WEBP", "image/webp", "evidence.webp"),
        )
        for image_format, content_type, filename in cases:
            with self.subTest(image_format=image_format):
                provider = detected_provider()
                result = await classify_image(
                    self.upload(
                        image_bytes(image_format), content_type, filename
                    ),
                    VisionAgent(provider),
                )
                self.assertTrue(result.detected)
                self.assertEqual(provider.calls, 1)

    async def test_jpeg_extension_and_image_jpg_alias_are_accepted(self) -> None:
        provider = detected_provider()
        result = await classify_image(
            self.upload(image_bytes("JPEG"), "image/jpg", "evidence.jpeg"),
            VisionAgent(provider),
        )

        self.assertTrue(result.detected)
        self.assertEqual(provider.calls, 1)

    async def test_mime_and_decoded_format_mismatch_is_rejected(self) -> None:
        provider = detected_provider()
        with self.assertRaises(HTTPException) as context:
            await classify_image(
                self.upload(png_bytes(), "image/jpeg", "renamed.jpg"),
                VisionAgent(provider),
            )

        self.assertEqual(context.exception.status_code, 415)
        self.assertIn("decoded image format PNG", context.exception.detail)
        self.assertEqual(provider.calls, 0)

    async def test_filename_does_not_select_the_classification(self) -> None:
        cracked = next(
            config
            for config in VISION_CATEGORIES
            if config.taxonomy_issue == "Cracked Road"
        )
        provider = FakeVisionProvider(
            {prompt: 0.45 for prompt in cracked.prompts}
        )
        result = await classify_image(
            self.upload(png_bytes(), "image/png", "overflowing_bin.png"),
            VisionAgent(provider),
        )

        self.assertEqual(result.taxonomy_issue, "Cracked Road")

    async def test_unsupported_media_type(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await classify_image(
                self.upload(b"GIF89a", "image/gif"),
                VisionAgent(detected_provider()),
            )

        self.assertEqual(context.exception.status_code, 415)

    async def test_corrupt_image(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await classify_image(
                self.upload(b"not a real png", "image/png"),
                VisionAgent(detected_provider()),
            )

        self.assertEqual(context.exception.status_code, 400)

    async def test_oversized_image(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await classify_image(
                self.upload(b"x" * (MAX_UPLOAD_BYTES + 1), "image/png"),
                VisionAgent(detected_provider()),
            )

        self.assertEqual(context.exception.status_code, 413)


if __name__ == "__main__":
    unittest.main()
