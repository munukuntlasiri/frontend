"""Tests for resolution verification without loading the real vision model."""

from io import BytesIO
import unittest

from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.agents.resolution_agent import (
    ResolutionAgent,
    UnsupportedResolutionTargetError,
)
from app.agents.vision_agent import MAX_UPLOAD_BYTES, VISION_CATEGORIES
from app.main import verify_resolution
from app.models.schemas import ResolutionAction, ResolutionDecision
from app.services.vision_service import get_vision_provider


class SequentialFakeProvider:
    """Return one deterministic prompt-score mapping per submitted image."""

    provider_name = "fake_test_provider"
    model_id = "fake-test-model"
    device = "cpu"

    def __init__(self, responses: list[dict[str, float]]) -> None:
        self.responses = responses
        self.calls = 0

    def score_prompts(self, image, prompts) -> list[float]:
        response = self.responses[self.calls]
        self.calls += 1
        return [response.get(prompt, 0.01) for prompt in prompts]


def target_config(category: str = "Road Damage", issue: str = "Pothole"):
    return next(
        config
        for config in VISION_CATEGORIES
        if (
            config.category == category and config.issue == issue
        ) or (
            config.taxonomy_category == category and config.taxonomy_issue == issue
        )
    )


def score_map(
    category: str = "Road Damage",
    issue: str = "Pothole",
    target_score: float = 0.50,
    control_score: float = 0.02,
    other_score: float = 0.01,
) -> dict[str, float]:
    target = target_config(category, issue)
    scores = {
        prompt: other_score
        for config in VISION_CATEGORIES
        for prompt in config.prompts
    }
    scores.update({prompt: target_score for prompt in target.prompts})
    scores.update(
        {
            prompt: control_score
            for config in VISION_CATEGORIES
            if config.is_control
            for prompt in config.prompts
        }
    )
    return scores


def png_bytes(size: tuple[int, int] = (32, 24)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color=(90, 100, 110)).save(output, format="PNG")
    return output.getvalue()


def encoded_image(image_format: str, size: tuple[int, int] = (32, 24)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color=(90, 100, 110)).save(
        output, format=image_format
    )
    return output.getvalue()


def agent_for(before: dict[str, float], after: dict[str, float]) -> ResolutionAgent:
    return ResolutionAgent(SequentialFakeProvider([before, after]))


class ResolutionAgentTests(unittest.TestCase):
    """Verify the conservative three-way resolution policy."""

    def test_strong_verified_case(self) -> None:
        result = agent_for(
            score_map(target_score=0.50),
            score_map(target_score=0.05, control_score=0.40),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole", "MI-200",
        )

        self.assertEqual(result.decision, ResolutionDecision.VERIFIED)
        self.assertEqual(
            result.recommended_action,
            ResolutionAction.REQUEST_CITIZEN_CONFIRMATION,
        )
        self.assertFalse(result.requires_human_review)
        self.assertEqual(result.issue_id, "MI-200")

    def test_clear_unsuccessful_case(self) -> None:
        result = agent_for(
            score_map(target_score=0.50),
            score_map(target_score=0.44),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNSUCCESSFUL)
        self.assertEqual(result.recommended_action, ResolutionAction.KEEP_OPEN)

    def test_borderline_case_is_uncertain(self) -> None:
        result = agent_for(
            score_map(target_score=0.50),
            score_map(target_score=0.16, control_score=0.12, other_score=0.08),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNCERTAIN)
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.recommended_action, ResolutionAction.HUMAN_REVIEW)

    def test_weak_before_evidence_is_uncertain(self) -> None:
        result = agent_for(
            score_map(target_score=0.08, control_score=0.30),
            score_map(target_score=0.03, control_score=0.35),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNCERTAIN)
        self.assertFalse(result.before_evidence.detected)
        self.assertIsNone(result.verification_score)

    def test_same_evidence_remains_unsuccessful(self) -> None:
        same_scores = score_map(target_score=0.50)
        result = agent_for(same_scores, same_scores).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNSUCCESSFUL)
        self.assertEqual(result.score_reduction, 0.0)

    def test_materially_worse_after_evidence_remains_unsuccessful(self) -> None:
        result = agent_for(
            score_map(target_score=0.25),
            score_map(target_score=0.75),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road Damage", "Pothole",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNSUCCESSFUL)
        self.assertEqual(result.score_reduction_ratio, -2.0)

    def test_different_supported_issue_uses_its_prompt_group(self) -> None:
        result = agent_for(
            score_map("Waste Management", "Garbage Accumulation", 0.55),
            score_map(
                "Waste Management", "Garbage Accumulation", 0.04, 0.42
            ),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Waste Management", "Garbage Accumulation",
        )

        self.assertEqual(result.decision, ResolutionDecision.VERIFIED)
        self.assertEqual(result.before_evidence.category, "Waste Management")

    def test_canonical_alias_preserves_existing_drainage_verification(self) -> None:
        result = agent_for(
            score_map("Water", "Drainage Overflow", 0.55),
            score_map("Water", "Drainage Overflow", 0.04, 0.42),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Water", "Drainage Overflow",
        )

        self.assertEqual(result.decision, ResolutionDecision.VERIFIED)
        self.assertEqual(result.before_evidence.category, "Drainage")
        self.assertEqual(result.before_evidence.issue, "Drainage Problem")
        self.assertEqual(result.before_evidence.taxonomy_category, "Water")
        self.assertEqual(result.before_evidence.taxonomy_issue, "Drainage Overflow")

    def test_unvalidated_new_issue_requires_human_review(self) -> None:
        result = agent_for(
            score_map("Road", "Cracked Road", 0.55),
            score_map("Road", "Cracked Road", 0.04, 0.42),
        ).verify(
            png_bytes(), "image/png", png_bytes(), "image/png",
            "Road", "Cracked Road",
        )

        self.assertEqual(result.decision, ResolutionDecision.UNCERTAIN)
        self.assertTrue(result.requires_human_review)
        self.assertEqual(result.recommended_action, ResolutionAction.HUMAN_REVIEW)
        self.assertTrue(any("has not been validated" in reason for reason in result.reasons))

    def test_corrupt_before_and_after_images_are_rejected(self) -> None:
        valid_scores = score_map()
        with self.assertRaisesRegex(ValueError, "Before evidence"):
            agent_for(valid_scores, valid_scores).verify(
                b"bad", "image/png", png_bytes(), "image/png",
                "Road Damage", "Pothole",
            )
        with self.assertRaisesRegex(ValueError, "After evidence"):
            agent_for(valid_scores, valid_scores).verify(
                png_bytes(), "image/png", b"bad", "image/png",
                "Road Damage", "Pothole",
            )

    def test_unsupported_category_issue_pair_is_rejected(self) -> None:
        with self.assertRaises(UnsupportedResolutionTargetError):
            agent_for(score_map(), score_map()).verify(
                png_bytes(), "image/png", png_bytes(), "image/png",
                "Road Damage", "Sinkhole",
            )


class ResolutionEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Verify multipart status handling with an injected fake provider."""

    @staticmethod
    def upload(data: bytes, content_type: str) -> UploadFile:
        return UploadFile(
            file=BytesIO(data),
            filename="evidence",
            headers=Headers({"content-type": content_type}),
        )

    async def test_unsupported_media_type(self) -> None:
        fake_agent = agent_for(score_map(), score_map())
        with self.assertRaises(HTTPException) as context:
            await verify_resolution(
                self.upload(b"GIF89a", "image/gif"),
                self.upload(png_bytes(), "image/png"),
                "Road Damage", "Pothole", None, fake_agent,
            )

        self.assertEqual(context.exception.status_code, 415)

    async def test_valid_jpeg_and_webp_reach_shared_validation_path(self) -> None:
        fake_agent = agent_for(
            score_map(target_score=0.50),
            score_map(target_score=0.05, control_score=0.40),
        )
        result = await verify_resolution(
            self.upload(encoded_image("JPEG"), "image/jpeg"),
            self.upload(encoded_image("WEBP"), "image/webp"),
            "Road Damage", "Pothole", "MI-IMAGE", fake_agent,
        )

        self.assertEqual(result.decision, ResolutionDecision.VERIFIED)

    async def test_mismatched_after_image_is_rejected(self) -> None:
        fake_agent = agent_for(score_map(), score_map())
        with self.assertRaises(HTTPException) as context:
            await verify_resolution(
                self.upload(encoded_image("JPEG"), "image/jpeg"),
                self.upload(png_bytes(), "image/jpeg"),
                "Road Damage", "Pothole", None, fake_agent,
            )

        self.assertEqual(context.exception.status_code, 415)
        self.assertIn("After evidence", context.exception.detail)

    async def test_oversized_image(self) -> None:
        fake_agent = agent_for(score_map(), score_map())
        with self.assertRaises(HTTPException) as context:
            await verify_resolution(
                self.upload(b"x" * (MAX_UPLOAD_BYTES + 1), "image/png"),
                self.upload(png_bytes(), "image/png"),
                "Road Damage", "Pothole", None, fake_agent,
            )

        self.assertEqual(context.exception.status_code, 413)


class ResolutionProviderReuseTests(unittest.TestCase):
    """Ensure normal tests do not initialize or download SigLIP."""

    def test_real_provider_remains_lazy(self) -> None:
        self.assertEqual(get_vision_provider().device, "not_loaded")


if __name__ == "__main__":
    unittest.main()
