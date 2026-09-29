"""Verify before-and-after civic issue evidence with conservative rules."""

from dataclasses import dataclass
import math

from PIL import Image

from app.agents.vision_agent import (
    MIN_CIVIC_RELATIVE_SCORE,
    MIN_CONTROL_MARGIN,
    MIN_RUNNER_UP_MARGIN,
    VISION_CATEGORIES,
    InvalidImageError,
    OversizedImageError,
    UnsupportedImageMediaTypeError,
    VisionCategoryConfig,
    VisionProvider,
    VisionProviderError,
    decode_uploaded_image,
)
from app.models.schemas import (
    ResolutionAction,
    ResolutionDecision,
    ResolutionEvidence,
    ResolutionVerification,
)

# Provisional MVP thresholds. These must be calibrated with representative paired
# civic evidence before production use; they are decision rules, not probabilities.
MIN_VERIFIED_ABSOLUTE_REDUCTION = 0.15
MIN_VERIFIED_REDUCTION_RATIO = 0.60
MAX_VERIFIED_AFTER_SCORE = 0.10
MAX_UNSUCCESSFUL_ABSOLUTE_REDUCTION = 0.10
MAX_UNSUCCESSFUL_REDUCTION_RATIO = 0.25
MAX_ASPECT_RATIO_DIFFERENCE = 0.25

RESOLUTION_LIMITATIONS: tuple[str, ...] = (
    "Scores are relative zero-shot prompt scores, not calibrated probabilities.",
    "Different viewpoints, distance, framing, lighting, weather, and occlusion can change scores.",
    "Matching aspect ratios and dimensions do not prove that both images show the same location.",
    "The MVP uses whole-image prompt scoring and does not localize defects with bounding boxes.",
    "New visual issue types require representative before/after validation before automated verification.",
    "A VERIFIED decision requests citizen confirmation and never closes an issue automatically.",
    "Streetlight evidence can verify visible physical damage only, not electrical operation.",
)


class UnsupportedResolutionTargetError(ValueError):
    """Raised when the supplied category and issue have no civic prompt group."""


@dataclass(frozen=True)
class _ScoredEvidence:
    target_score: float
    target_top_prompt: str
    target_detected: bool
    control_score: float
    highest_other_civic_score: float


class ResolutionAgent:
    """Compare target issue evidence using the shared local vision provider."""

    def __init__(self, provider: VisionProvider) -> None:
        self._provider = provider

    def verify(
        self,
        before_bytes: bytes,
        before_content_type: str | None,
        after_bytes: bytes,
        after_content_type: str | None,
        category: str,
        issue: str,
        issue_id: str | None = None,
    ) -> ResolutionVerification:
        """Validate two images and return a conservative resolution recommendation."""

        target = self._find_target(category, issue)
        before_image = self._decode_evidence(
            "Before evidence", before_bytes, before_content_type
        )
        after_image = self._decode_evidence(
            "After evidence", after_bytes, after_content_type
        )
        before = self._score_image(before_image, target)
        after = self._score_image(after_image, target)

        reduction = before.target_score - after.target_score
        reduction_ratio = (
            reduction / before.target_score if before.target_score > 0.0 else None
        )
        aspect_ratio_difference = self._aspect_ratio_difference(
            before_image, after_image
        )
        comparable_aspect_ratio = (
            aspect_ratio_difference <= MAX_ASPECT_RATIO_DIFFERENCE
        )

        reasons = [
            f"Before target relative score {before.target_score:.4f}; target evidence "
            f"{'passed' if before.target_detected else 'failed'} the provisional consistency gates.",
            f"After target relative score {after.target_score:.4f}; absolute reduction "
            f"{reduction:.4f}.",
            (
                f"Proportional target-score reduction {reduction_ratio:.4f}."
                if reduction_ratio is not None
                else "Proportional reduction is unavailable because the before score is zero."
            ),
            f"After control relative score {after.control_score:.4f} compared with target "
            f"score {after.target_score:.4f}.",
            f"Image aspect-ratio difference {aspect_ratio_difference:.4f}; provisional "
            f"maximum {MAX_ASPECT_RATIO_DIFFERENCE:.2f}.",
        ]
        if before_image.size != after_image.size:
            reasons.append(
                "Before and after pixel dimensions differ; resolution changes can influence model evidence."
            )

        verified = (
            target.automatic_resolution_supported
            and before.target_detected
            and comparable_aspect_ratio
            and reduction >= MIN_VERIFIED_ABSOLUTE_REDUCTION
            and reduction_ratio is not None
            and reduction_ratio >= MIN_VERIFIED_REDUCTION_RATIO
            and after.target_score <= MAX_VERIFIED_AFTER_SCORE
            and after.control_score > after.target_score
        )
        unsuccessful = (
            target.automatic_resolution_supported
            and before.target_detected
            and comparable_aspect_ratio
            and after.target_detected
            and (
                reduction <= MAX_UNSUCCESSFUL_ABSOLUTE_REDUCTION
                or (
                    reduction_ratio is not None
                    and reduction_ratio <= MAX_UNSUCCESSFUL_REDUCTION_RATIO
                )
            )
        )

        if verified:
            decision = ResolutionDecision.VERIFIED
            action = ResolutionAction.REQUEST_CITIZEN_CONFIRMATION
            requires_human_review = False
            reasons.append(
                "Strong target-score reduction and normal-scene evidence passed all provisional verification gates."
            )
        elif unsuccessful:
            decision = ResolutionDecision.UNSUCCESSFUL
            action = ResolutionAction.KEEP_OPEN
            requires_human_review = False
            reasons.append(
                "The target issue remains detected without enough reduction; keep the issue open."
            )
        else:
            decision = ResolutionDecision.UNCERTAIN
            action = ResolutionAction.HUMAN_REVIEW
            requires_human_review = True
            reasons.append(
                self._uncertain_reason(target, before, comparable_aspect_ratio)
            )

        verification_score = (
            round(max(0.0, min(1.0, reduction_ratio)), 6)
            if before.target_detected and reduction_ratio is not None
            else None
        )
        return ResolutionVerification(
            issue_id=issue_id.strip() if issue_id and issue_id.strip() else None,
            decision=decision,
            verification_score=verification_score,
            before_evidence=self._to_evidence(target, before, before_image),
            after_evidence=self._to_evidence(target, after, after_image),
            issue_score_before=round(before.target_score, 6),
            issue_score_after=round(after.target_score, 6),
            score_reduction=round(reduction, 6),
            score_reduction_ratio=(
                round(reduction_ratio, 6) if reduction_ratio is not None else None
            ),
            reasons=reasons,
            limitations=list(RESOLUTION_LIMITATIONS),
            requires_human_review=requires_human_review,
            recommended_action=action,
        )

    @staticmethod
    def _find_target(category: str, issue: str) -> VisionCategoryConfig:
        normalized_category = category.strip().casefold()
        normalized_issue = issue.strip().casefold()
        for config in VISION_CATEGORIES:
            if config.is_control or config.issue is None:
                continue
            legacy_match = (
                config.category.casefold() == normalized_category
                and config.issue.casefold() == normalized_issue
            )
            taxonomy_match = (
                config.taxonomy_issue is not None
                and config.taxonomy_category.casefold() == normalized_category
                and config.taxonomy_issue.casefold() == normalized_issue
            )
            if legacy_match or taxonomy_match:
                return config
        raise UnsupportedResolutionTargetError(
            "Unsupported category/issue pair for resolution verification."
        )

    @staticmethod
    def _decode_evidence(
        label: str, image_bytes: bytes, content_type: str | None
    ) -> Image.Image:
        try:
            return decode_uploaded_image(image_bytes, content_type)
        except (
            UnsupportedImageMediaTypeError,
            OversizedImageError,
            InvalidImageError,
        ) as exc:
            raise type(exc)(f"{label}: {exc}") from exc

    def _score_image(
        self, image: Image.Image, target: VisionCategoryConfig
    ) -> _ScoredEvidence:
        prompt_entries = [
            (config, prompt)
            for config in VISION_CATEGORIES
            for prompt in config.prompts
        ]
        scores = self._provider.score_prompts(
            image, [prompt for _, prompt in prompt_entries]
        )
        if len(scores) != len(prompt_entries):
            raise VisionProviderError(
                "Vision provider returned a different number of scores than prompts."
            )
        if any(
            not math.isfinite(score) or score < 0.0 or score > 1.0
            for score in scores
        ):
            raise VisionProviderError("Vision provider returned an invalid prompt score.")

        grouped: dict[str, tuple[float, str, VisionCategoryConfig]] = {}
        offset = 0
        for config in VISION_CATEGORIES:
            group_scores = scores[offset : offset + len(config.prompts)]
            offset += len(config.prompts)
            top_index = max(range(len(group_scores)), key=group_scores.__getitem__)
            grouped[config.label] = (
                sum(group_scores) / len(group_scores),
                config.prompts[top_index],
                config,
            )

        target_score, target_prompt, _ = grouped[target.label]
        control_score = next(
            score for score, _, config in grouped.values() if config.is_control
        )
        other_scores = [
            score
            for score, _, config in grouped.values()
            if not config.is_control and config.label != target.label
        ]
        highest_other = max(other_scores)
        detected = (
            target_score >= MIN_CIVIC_RELATIVE_SCORE
            and target_score - control_score >= MIN_CONTROL_MARGIN
            and target_score - highest_other >= MIN_RUNNER_UP_MARGIN
        )
        return _ScoredEvidence(
            target_score=target_score,
            target_top_prompt=target_prompt,
            target_detected=detected,
            control_score=control_score,
            highest_other_civic_score=highest_other,
        )

    @staticmethod
    def _aspect_ratio_difference(before: Image.Image, after: Image.Image) -> float:
        before_ratio = before.width / before.height
        after_ratio = after.width / after.height
        return abs(before_ratio - after_ratio) / max(before_ratio, after_ratio)

    @staticmethod
    def _to_evidence(
        target: VisionCategoryConfig,
        scored: _ScoredEvidence,
        image: Image.Image,
    ) -> ResolutionEvidence:
        return ResolutionEvidence(
            category=target.category,
            issue=target.issue or target.label,
            taxonomy_category=target.taxonomy_category,
            taxonomy_issue=target.taxonomy_issue or target.label,
            relative_score=round(scored.target_score, 6),
            detected=scored.target_detected,
            top_prompt=scored.target_top_prompt,
            image_width=image.width,
            image_height=image.height,
        )

    @staticmethod
    def _uncertain_reason(
        target: VisionCategoryConfig,
        before: _ScoredEvidence,
        comparable_aspect_ratio: bool,
    ) -> str:
        if not target.automatic_resolution_supported:
            return (
                f"{target.taxonomy_category} / {target.taxonomy_issue} is implemented "
                "for classification but has not been validated for automated before/after "
                "verification; human review is required."
            )
        if not before.target_detected:
            return (
                "The before image does not consistently establish the supplied target issue; human review is required."
            )
        if not comparable_aspect_ratio:
            return (
                "The image aspect ratios are too different for an automated decision; human review is required."
            )
        return (
            "The score change is borderline or conflicting and does not meet verified or unsuccessful gates."
        )
